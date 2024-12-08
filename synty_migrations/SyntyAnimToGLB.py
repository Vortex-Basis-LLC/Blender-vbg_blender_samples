import glob
import math
import time

import bpy
import os
import mathutils
from typing import Generator, List, Tuple
from attr import dataclass

# Purpose: This script is intended to take the Synty Locomotion and Sword animation packages and re-map them onto a character with a T-Pose.
#   But, it could probably generally be used for remapping animations between armatures with same bone names and approximate general proportions.

# USAGE:
# 1. (Replace armature with a different one with same bones if desired)
# 2. Update target_armature_name below if needed.
# 3. Ensure you have Synty Locomotion and/or Sword Animation pack imported into Unity (or extract unitypackage into a folder).
# 4. Modify base_synty_animation_path 
# 5. Modify export_sets as desired below.
# 6. Modify export_path for where exported GLBs should be saved (one per export set).

# KNOWN ISSUES:
# 1. "-loop" on the NLA track names is not carrying into Godot.
# 2. Synty animation specific:
#    - Right third finger is not aligned properly. Need to extra steps to adjust this.
#    - Options: Possibly adjust the keyframes directly in code for that finger, delete the track for that finger or copy from second finger?
# 3. There appears to be a slight hitch when looping the animations in Godot.
#    - Not sure if this is just a glitch in previewer.
# 4. Some of the sword animations come across in Godot with a very delayed start time.
#    - Need to see if wrong collection of frames is being included (or if that's just how they are in Blender too).
#    - Specific Example: A_Attack_HeavyCombo01A_ReturnToIdle_Sword
#    - Enabling "Trimming" on import options for Animation Library seems to fix this,
#      but maybe should look into doing the trimming on Blender side.

target_armature_name = 'Armature'
export_path = '/home/geo/dev/tools/Blender-vbg_blender_samples/synty_migrations/export/'
fixup_synty_third_finger = True
base_synty_animation_path = '/home/geo/Documents/Game Assets/Polygon/Animations/'
base_synty_locomotion_path = os.path.join(base_synty_animation_path, 'AnimationBaseLocomotion/Animations')
base_synty_sword_path = os.path.join(base_synty_animation_path, 'AnimationSwordCombat/Animations')


def sanity_check_project_is_as_intended():
    target_armature = bpy.data.objects.get(target_armature_name)
    if target_armature is None:
        print("Object for target_armature_name not found:", target_armature_name)
        return False

    for obj in bpy.data.objects:
        # We assume we won't care about top-level armatures that are not the target armature.
        if obj.parent is None:
            if obj != target_armature:
                print(
                    "Target armature should be only top-level object in the project. You probably don't want to run this script here. It will mostly delete everything else except target armature when done.")
                return False

    if not os.path.exists(export_path):
        print("Export path does not exist:", export_path)
        return False

    return True


def remove_all_unused_animation_actions_in_file():
    for action in bpy.data.actions:
        if (action.users == 0) or (action.users == 1 and action.use_fake_user):
            bpy.data.actions.remove(action)


def clear_animation_action_on_armature(armature):
    if armature.animation_data is None:
        return
    armature.animation_data.action = None


def delete_all_nla_tracks_on_armature(armature):
    track_list = []
    if armature.animation_data is None:
        return
    for track in armature.animation_data.nla_tracks:
        track_list.append(track)
    for track in track_list:
        armature.animation_data.nla_tracks.remove(track)


def remove_all_copy_transforms_bone_constraints_on_armature(target_armature):
    for target_pose_bone in target_armature.pose.bones:
        constraints_to_delete = [c for c in target_pose_bone.constraints if
                                 c.type == 'COPY_TRANSFORMS' or c.type == 'COPY_LOCATION' or c.type == 'COPY_ROTATION']
        for constraint in constraints_to_delete:
            target_pose_bone.constraints.remove(constraint)


def add_copy_transforms_constraints_to_all_bones(source_armature, target_armature, offsets):
    for target_bone in target_armature.pose.bones:
        if target_bone.name in source_armature.pose.bones:

            loc_constraint = target_bone.constraints.new('COPY_LOCATION')
            loc_constraint.target = source_armature
            loc_constraint.subtarget = target_bone.name
            loc_constraint.target_space = 'LOCAL'
            loc_constraint.owner_space = 'LOCAL'
            loc_constraint.use_offset = True
            loc_constraint.influence = 1.0

            rot_constraint = target_bone.constraints.new('COPY_ROTATION')
            rot_constraint.target = source_armature
            rot_constraint.subtarget = target_bone.name
            # rot_constraint.target_space = 'LOCAL'
            # rot_constraint.owner_space = 'LOCAL'
            rot_constraint.influence = 1.0

            if target_bone.name == "Root":
                target_bone.matrix_basis.translation -= offsets["Hips"]
                print(f"{target_bone.name} final location: {target_bone.matrix_basis.translation}")
                bpy.context.view_layer.update()


def apply_animation_constraints_per_frame(target_armature, frame_from, frame_to):
    bpy.context.view_layer.objects.active = target_armature
    bpy.ops.object.mode_set(mode='POSE')
    for target_bone in target_armature.data.bones:
        target_armature.data.bones.active = target_bone
    ks = bpy.data.scenes["Scene"].keying_sets_all
    ks.active = ks['Location & Rotation']
    scene = bpy.context.scene
    for frame in range(frame_from, frame_to + 1):
        scene.frame_set(frame)
        # Apply transforms for this frame.
        bpy.ops.pose.visual_transform_apply()

        # Insert key frame for this frame
        for bone in target_armature.pose.bones:
            bone.keyframe_insert(data_path="location")
            bone.keyframe_insert(data_path="rotation_quaternion")


def rotate_keyframe_points(target_action, target_path, angle, axis='Y'):
    # Rotating the keyframe points may be needed if there is a misalignment in the source animations.

    fcurves = target_action.fcurves

    first_curve = fcurves.find(target_path, index=0)
    keyframe_point_len = len(first_curve.keyframe_points)

    for keyframe_point_index in range(keyframe_point_len):
        q_array = []
        for index in range(4):
            target_curve = fcurves.find(target_path, index=index)
            target_keyframe = target_curve.keyframe_points[keyframe_point_index]
            target_co = getattr(target_keyframe, 'co')

            q_array.append(target_co[1])

        q = mathutils.Quaternion((q_array[0], q_array[1], q_array[2], q_array[3]))

        mat_rotate_around_axis = mathutils.Matrix.Rotation(angle, 4, axis)
        q_rotate_around_axis = mat_rotate_around_axis.to_quaternion()

        new_q = q @ q_rotate_around_axis
        new_q_array = [new_q.w, new_q.x, new_q.y, new_q.z]

        for index in range(4):
            target_curve = fcurves.find(target_path, index=index)
            target_keyframe = target_curve.keyframe_points[keyframe_point_index]

            # Fix quaternion value.
            target_co = getattr(target_keyframe, 'co')
            target_co[1] = new_q_array[index]

            # Fix interpolation handles.
            # TODO: Is this actually the best handle position for smoothing the transitions?
            target_handle_left = getattr(target_keyframe, 'handle_left')
            target_handle_left[0] = target_co[0] - 0.4
            target_handle_left[1] = target_co[1]

            target_handle_right = getattr(target_keyframe, 'handle_right')
            target_handle_right[0] = target_co[0] + 0.4
            target_handle_right[1] = target_co[1]


def push_armature_action_to_new_nla_strip(armature, frame_from, track_name, strip_name):
    if armature.animation_data is not None:
        action = armature.animation_data.action
        if action is not None:
            track = armature.animation_data.nla_tracks.new()
            track.name = track_name
            strip = track.strips.new(strip_name, 1, action)
            strip.name = strip_name
            track.lock = True
            track.mute = True
            clear_animation_action_on_armature(armature)


def delete_blender_object(obj_to_delete):
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj_to_delete.select_set(True)
    bpy.ops.object.delete()


@dataclass
class ExportSet:
    export_name: str
    fbxs: List[str] = []


def clear_and_reset_armature(armature):
    clear_animation_action_on_armature(armature)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    for bone in armature.pose.bones:
        bone.location = (0, 0, 0)
        bone.rotation_quaternion = (1, 0, 0, 0)
        bone.scale = (1, 1, 1)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()


def do_custom_animation_fixups(target_armature):
    # Handle special tweaking for animations here.
    if fixup_synty_third_finger:
        # The synty animations need to have their third finger rotation fixed.
        rotate_keyframe_points(
            target_armature.animation_data.action,
            'pose.bones["Finger_03"].rotation_quaternion',
            math.pi,
            axis='Y')

        rotate_keyframe_points(
            target_armature.animation_data.action,
            'pose.bones["Finger_04"].rotation_quaternion',
            -math.pi / 2.0,
            axis='Z')


def do_animation_imports_exports_main(export_set: ExportSet):
    export_name = export_set.export_name
    target_armature = bpy.data.objects[target_armature_name]
    delete_all_nla_tracks_on_armature(target_armature)
    clear_animation_action_on_armature(target_armature)
    remove_all_unused_animation_actions_in_file()

    print("Export Name:", export_name)
    for fbx_path in export_set.fbxs:
        process_fbx(fbx_path, target_armature)
        gltf_export(export_name)


def calculate_initial_offsets(source_armature, target_armature):
    offsets = {}
    for bone_name in target_armature.pose.bones.keys():
        if bone_name in source_armature.pose.bones:
            source_bone = source_armature.pose.bones[bone_name]
            target_bone = target_armature.pose.bones[bone_name]

            # Calculate the offset in world space
            source_world_matrix = source_bone.matrix
            target_world_matrix = target_bone.matrix

            source_translation = source_world_matrix.to_translation()
            target_translation = target_world_matrix.to_translation()

            offset = target_translation - source_translation
            offsets[bone_name] = offset

            print(f"Offset for {bone_name} calculated: {offset}")
    return offsets


def process_fbx(fbx_path, target_armature):
    base_file_name = os.path.splitext(os.path.basename(fbx_path))[0]
    print("FILE: ", fbx_path, " ", base_file_name)

    remove_all_unused_animation_actions_in_file()

    print("Target armature position:", target_armature.location)

    bpy.ops.import_scene.fbx(filepath=fbx_path, automatic_bone_orientation=True)
    source_armature_list = get_source_armatures(target_armature)

    for source_armature in source_armature_list:
        if source_armature.animation_data is None or source_armature.animation_data.action is None:
            continue

        print("Source armature position:", source_armature.location)
        source_action = source_armature.animation_data.action
        frame_from = int(source_action.frame_range[0])
        frame_to = int(source_action.frame_range[1])
        print("Copying Animation:", source_armature.name, "; Frames:", frame_from, "to", frame_to)

        remove_all_copy_transforms_bone_constraints_on_armature(target_armature)
        add_copy_transforms_constraints_to_all_bones(source_armature, target_armature,
                                                     calculate_initial_offsets(source_armature, target_armature))
        apply_animation_constraints_per_frame(target_armature, frame_from, frame_to)
        remove_all_copy_transforms_bone_constraints_on_armature(target_armature)
        do_custom_animation_fixups(target_armature)

        anim_name = base_file_name
        if should_loop(anim_name):
            anim_name = anim_name + '-loop'
        push_armature_action_to_new_nla_strip(target_armature, frame_from, anim_name, anim_name)

        print("Removing:", source_armature.name)
        delete_blender_object(source_armature)

    remove_all_unused_animation_actions_in_file()
    clear_and_reset_armature(target_armature)


def should_loop(anim_name: str):
    return (any(word in anim_name.lower() for word in {"idle", "crouch", "walk", "strafe", "fall", "run", "loop", "turn"}) 
            and all(word not in anim_name.lower() for word in {"hit", "begin", "end", "_to", "_returnto", "jump", "attack"}))

def gltf_export(export_name):
    full_export_path = os.path.join(export_path, export_name + '.glb')
    print("Export:", full_export_path)
    bpy.ops.export_scene.gltf(
        filepath=full_export_path,
        export_format='GLB'
    )


def get_source_armatures(target_armature):
    source_armature_list = []
    for obj in bpy.data.objects:
        if obj.parent is None:
            if obj != target_armature:
                if obj.type == 'ARMATURE':
                    source_armature_list.append(obj)
    return source_armature_list


def get_fbx_dirs(folder_path: str, name: str) -> Generator[ExportSet, None, None]:
    for dir_name in os.listdir(folder_path):
        full_path = os.path.join(folder_path, dir_name)
        if os.path.isdir(full_path):
            regular_fbx, root_motion_fbx = filter_fbx_files(full_path)
            output_name = f"{name}_{dir_name}"
            if regular_fbx:
                yield ExportSet(output_name, regular_fbx)
            if root_motion_fbx:
                yield ExportSet(f"{output_name}_root", root_motion_fbx)
            yield from get_fbx_dirs(full_path, f"{name}_{dir_name.lower()}")


def filter_fbx_files(directory: str) -> Tuple[List[str], List[str]]:
    all_fbx_files = glob.glob(os.path.join(directory, "*.fbx"))
    regular_fbx = [fbx for fbx in all_fbx_files if "RootMotion" not in fbx]
    root_motion_fbx = [fbx for fbx in all_fbx_files if "RootMotion" in fbx]
    return regular_fbx, root_motion_fbx


if not sanity_check_project_is_as_intended():
    print("Sanity checks failed. See messages above.")
else:
    start_time = time.time()
    export_sets = (list(get_fbx_dirs(base_synty_locomotion_path, "locomotion", True)) +
                   list(get_fbx_dirs(base_synty_sword_path, "sword", True)))

    for export_set in export_sets:
        do_animation_imports_exports_main(export_set)

    print("Purge unused data...")
    bpy.ops.outliner.orphans_purge()

    end_time = time.time()
    print("Total Time (seconds):", int(end_time - start_time))
