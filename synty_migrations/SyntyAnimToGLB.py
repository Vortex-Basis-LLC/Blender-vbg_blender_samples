import bpy
import os
import sys
import time
import mathutils
import math

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
export_path = 'D:/Temp/SyntyExport/'

# If this is set to true, this will attempt to fix the third finger of right hand having the last two bones at strange angles.
# Turning this off by default for now since it doesn't seem to be the correct change to make for all of the characters.
fixup_synty_third_finger = False


# NOTE: Define the "exports_sets" below to decide what will be converted to GLB files.
class CustomAnimExportSet:
    export_name = ''
    root_path = ''
    loop = True
    filename_must_have = None
    filename_must_not_have = None
    
    def __init__(
            self, 
            export_name, 
            root_path, 
            loop = False, 
            filename_must_have = None,
            filename_must_not_have = None
        ):
        self.export_name = export_name
        self.root_path = root_path
        self.loop = loop
        self.filename_must_have = filename_must_have
        self.filename_must_not_have = filename_must_not_have


base_synty_animation_path = 'D:/Unity/TestProjects/Unity2022Test/Assets/Synty'
base_synty_locomotion_path = os.path.join(base_synty_animation_path, 'AnimationBaseLocomotion/Animations/Polygon')
base_synty_sword_path = os.path.join(base_synty_animation_path, 'AnimationSwordCombat/Animations/Polygon')
        
        
export_sets = [
    # 
    # Locomotion
    #
    CustomAnimExportSet(
        'synty_locomotion_masc_root', 
        os.path.join(base_synty_locomotion_path,'Masculine'),
        loop = True,
        filename_must_have = "RootMotion"
    ), 
    CustomAnimExportSet(
        'synty_locomotion_masc', 
        os.path.join(base_synty_locomotion_path,'Masculine'),
        loop = True,
        filename_must_not_have = "RootMotion"
    ), 
    CustomAnimExportSet(
        'synty_locomotion_fem_root', 
        os.path.join(base_synty_locomotion_path,'Feminine'),
        loop = True, 
        filename_must_have = "RootMotion"
    ),
    CustomAnimExportSet(
        'synty_locomotion_fem', 
        os.path.join(base_synty_locomotion_path,'Feminine'),
        loop = True,
        filename_must_not_have = "RootMotion"
    ),
    CustomAnimExportSet(
        'synty_locomotion_neutral', 
        os.path.join(base_synty_locomotion_path,'Neutral'),
        True # Loop
    ),
    
    # 
    # Sword
    #
    CustomAnimExportSet(
        'synty_sword_attack', 
        os.path.join(base_synty_sword_path,'Attack'),
        loop = False
    ),
    CustomAnimExportSet(
        'synty_sword_block', 
        os.path.join(base_synty_sword_path,'Block'),
        loop = False
    ),
    CustomAnimExportSet(
        'synty_sword_death', 
        os.path.join(base_synty_sword_path,'Death'),
        loop = False
    ),
    CustomAnimExportSet(
        'synty_sword_dodge', 
        os.path.join(base_synty_sword_path,'Dodge'),
        loop = False
    ),
    CustomAnimExportSet(
        'synty_sword_hit', 
        os.path.join(base_synty_sword_path,'Hit'),
        loop = False
    ),
    CustomAnimExportSet(
        'synty_sword_idle', 
        os.path.join(base_synty_sword_path,'Idle'),
        loop = False
    )
]

        

    


def sanity_check_project_is_as_intended():
    target_armature = bpy.data.objects.get(target_armature_name)
    if target_armature is None:
        print("Object for target_armature_name not found:", target_armature_name)
        return False
    
    for obj in bpy.data.objects:
        # We assume we won't care about top-level armatures that are not the target armature.
        if obj.parent is None:
            if obj != target_armature:
                print("Target armature should be only top-level object in the project. You probably don't want to run this script here. It will mostly delete everything else except target armature when done.")
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
        constraints_to_delete = [ c for c in target_pose_bone.constraints if c.type == 'COPY_TRANSFORMS' or c.type == 'COPY_LOCATION' or c.type == 'COPY_ROTATION' ]
        for constraint in constraints_to_delete:
            target_pose_bone.constraints.remove(constraint)


def add_copy_transforms_constraints_to_all_bones(source_armature, target_armature):   
    remove_all_copy_transforms_bone_constraints_on_armature(target_armature)
        
    # TODO: Support a bone mapping if names aren't exact matches.
        
    for source_pose_bone in source_armature.pose.bones:
        source_bone = source_armature.data.bones[source_pose_bone.name]
       
        target_bone = target_armature.data.bones.get(source_pose_bone.name)

        if target_bone is None:
            print("BONE NOT FOUND:", source_pose_bone.name)
        else:
            target_pose_bone = target_armature.pose.bones[source_pose_bone.name]
            
            target_pose_bone.constraints.new('COPY_ROTATION') 
            new_constraint = target_pose_bone.constraints[-1]
            new_constraint.name = "Copy Rotation"
            new_constraint.target = source_armature
            new_constraint.subtarget = source_pose_bone.name
            new_constraint.mix_mode = "REPLACE"
            
            target_pose_bone.constraints.new('COPY_LOCATION') 
            new_constraint = target_pose_bone.constraints[-1]
            new_constraint.name = "Copy Location"
            new_constraint.target = source_armature
            new_constraint.subtarget = source_pose_bone.name
            new_constraint.owner_space = "WORLD"
            new_constraint.target_space = "WORLD"



def apply_animation_constraints_per_frame(target_armature, frame_from, frame_to):
    bpy.context.view_layer.objects.active = target_armature
    bpy.ops.object.mode_set(mode='POSE')
    
    for target_bone in target_armature.data.bones:
        target_armature.data.bones.active = target_bone
    
    ks = bpy.data.scenes["Scene"].keying_sets_all
    ks.active = ks['Location & Rotation']
        
    scene = bpy.context.scene
    for frame in range(frame_from, frame_to):
        scene.frame_current = frame
        scene.frame_set(scene.frame_current)

        # Apply transforms for this frame.
        bpy.ops.pose.visual_transform_apply()

        # Insert key frame for this frame.
        bpy.ops.anim.keyframe_insert_menu(type='__ACTIVE__')



def rotate_keyframe_points(target_action, target_path, angle, axis = 'Y'):
    # Rotating the keyframe points may be needed if there is a misalignment in the source animations.
    
    fcurves = target_action.fcurves

    first_curve = fcurves.find(target_path, index = 0)
    keyframe_point_len = len(first_curve.keyframe_points)

    for keyframe_point_index in range(keyframe_point_len):
        q_array = []
        for index in range(4):
            target_curve = fcurves.find(target_path, index = index)
            target_keyframe = target_curve.keyframe_points[keyframe_point_index]
            target_co = getattr(target_keyframe, 'co')
                
            q_array.append(target_co[1])
           
        q = mathutils.Quaternion((q_array[0], q_array[1], q_array[2], q_array[3]))

        mat_rotate_around_axis = mathutils.Matrix.Rotation(angle, 4, axis)
        q_rotate_around_axis = mat_rotate_around_axis.to_quaternion()

        new_q = q @ q_rotate_around_axis
        new_q_array = [new_q.w, new_q.x, new_q.y, new_q.z]

        for index in range(4):
            target_curve = fcurves.find(target_path, index = index)
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


def crawl_folders_for_anims(folder_path, out_filepaths, export_set):
    path_contents = os.listdir(folder_path)
    for filename in path_contents:
        filename_lower = filename.lower()
        
        full_path = os.path.join(folder_path, filename)
        if os.path.isdir(full_path):
            crawl_folders_for_anims(full_path, out_filepaths, export_set)
        elif filename_lower.endswith('.fbx'):
            include = True
            
            if export_set.filename_must_have is not None:
                if export_set.filename_must_have.lower() not in filename_lower:
                    include = False
                    
            if export_set.filename_must_not_have is not None:
                if export_set.filename_must_not_have.lower() in filename_lower:
                    include = False
            
            if include:
                out_filepaths.append(full_path)



def delete_blender_object(obj_to_delete):
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    obj_to_delete.select_set(True)
    bpy.ops.object.delete()

    # NOTE: The following might be part of a way to delete objects, but it doesn't seem to fully remove the armature.
#    obj_to_delete.parent = None
#    bpy.data.objects.remove(obj_to_delete, do_unlink=True, do_ui_user=True)
       
       

def do_custom_animation_fixups(target_armature):
    # Handle special tweaking for animations here.
    if fixup_synty_third_finger:
        # The synty animations need to have their third finger rotation fixed.
        rotate_keyframe_points(
            target_armature.animation_data.action,
            'pose.bones["Finger_03"].rotation_quaternion',
            math.pi,
            axis = 'Y')
            
        rotate_keyframe_points(
            target_armature.animation_data.action,
            'pose.bones["Finger_04"].rotation_quaternion',
            -math.pi / 2.0,
            axis = 'Z')


def do_animation_imports_exports_main(export_set):
    path = export_set.root_path
    export_name = export_set.export_name
    
    target_armature = bpy.data.objects[target_armature_name]

    delete_all_nla_tracks_on_armature(target_armature)
    clear_animation_action_on_armature(target_armature)
    remove_all_unused_animation_actions_in_file()


    print("Export Name:", export_name)
    print("Searching for animations:", path)

    fbx_filepaths = []
    crawl_folders_for_anims(path, fbx_filepaths, export_set)

    for filepath in fbx_filepaths:
        base_file_name = os.path.splitext(os.path.basename(filepath))[0]
        print("FILE: ", filepath, " ", base_file_name)
        
        # Import the model file. We will need to look for new objects that are not the original target armature.
        remove_all_unused_animation_actions_in_file()
        bpy.ops.import_scene.fbx(filepath = filepath, automatic_bone_orientation = True)
       
        source_armature_list = []
       
        # Every object that is not the target armature is currently assumed to be a new imported armature with animation data.
        # TODO: Build list of existing objects up front, so we can know which are actually new.
        for obj in bpy.data.objects:
            # We assume we won't care about top-level armatures that are not the target armature.
            if obj.parent is None:
                if obj != target_armature:
                    if obj.type == 'ARMATURE':
                        source_armature_list.append(obj)
               
        for source_armature in source_armature_list:        
            # Get the frame range for the source_armature animation action.
            if source_armature.animation_data is not None:
                if source_armature.animation_data.action is not None:
                    source_action = source_armature.animation_data.action
                    frame_from = int(source_action.frame_range[0])
                    frame_to = int(source_action.frame_range[1])
                    
                    print("Copying Animation:", source_armature.name, "; Frames:", frame_from, "to", frame_to)
                                  
                    add_copy_transforms_constraints_to_all_bones(source_armature, target_armature)
                    
                    apply_animation_constraints_per_frame(target_armature, frame_from, frame_to)                
                    
                    remove_all_copy_transforms_bone_constraints_on_armature(target_armature)     
                    
                    do_custom_animation_fixups(target_armature)                       
                    
                    # TODO: The NLA animation track name should determine the animation name when imported into Godot.
                    # TODO: Why is '-loop' not getting carried into Godot? Seems like it might be looping still?
                    anim_name = base_file_name
                    if export_set.loop:
                        # Allow Godot to mark this as looping.
                        anim_name = anim_name + '-loop'
                        
                    push_armature_action_to_new_nla_strip(target_armature, frame_from, anim_name, anim_name)
            
        # Delete the imported source objects.
        for source_armature in source_armature_list:
            print("Removing:", source_armature.name)
            delete_blender_object(source_armature)
            

    # Export the armature with the generated NLA tracks.        

    clear_animation_action_on_armature(target_armature)    
    remove_all_unused_animation_actions_in_file()
            
    full_export_path = os.path.join(export_path, export_name + '.glb')
    print("Export:", full_export_path)
                     
    bpy.ops.export_scene.gltf(
        filepath=full_export_path,
        export_format='GLB'
    )      



if not sanity_check_project_is_as_intended():
    print("Sanity checks failed. See messages above.")
else:
    start_time = time.time()
    
    for export_set in export_sets:
        do_animation_imports_exports_main(export_set)
        
    print("Purge unused data...")
    bpy.ops.outliner.orphans_purge()
        
    end_time = time.time()
    
    print("Total Time (seconds):", int(end_time - start_time))
