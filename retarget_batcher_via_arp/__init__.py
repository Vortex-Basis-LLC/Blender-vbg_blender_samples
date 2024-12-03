# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
import os

from . import retarget_helpers
from . import retarget_anim_export_set

RetargetAnimExportSet = retarget_anim_export_set.RetargetAnimExportSet

class SCENE_OP_retarget_batcher(bpy.types.Operator):
	"""Retarget a series of animations onto a target rig."""

	bl_idname = 'retargetbatcher_via_arp.retarget'
	bl_label = 'Batch Retarget'
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		# TODO: Ensure Auto-Rig Pro has been configured with target rig and bone map.
		return context.mode == 'OBJECT'
	

	def execute(self, context):
		scene = bpy.context.scene

		# Confirm that bone map has been set up in Auto-Rig Pro.
		if len(bpy.context.scene.bones_map_v2) == 0:
			self.report({'ERROR'}, 'Setup target armature and bone map in Auto-Rig Pro Remap first.')
			return {'CANCELLED'}

		if not os.path.exists(bpy.context.scene.retarget_batcher_import_path):
			self.report({'ERROR'}, 'Import path not specified.')
			return {'CANCELLED'}

		export_set_name = scene.retarget_batcher_export_set_name
		if export_set_name == None or export_set_name == '':
			export_set_name = 'anim_export_set'

		export_set = RetargetAnimExportSet(
			export_set_name,
			os.path.join(bpy.context.scene.retarget_batcher_import_path),
			loop = True
		)

		fbx_filepaths = []
		export_set.crawl_folders_for_anims(export_set.root_path, fbx_filepaths)


		target_rig_name = scene.target_rig
		target_rig = scene.objects[target_rig_name]

		# Clear current NLA tracks, so that we only have the new NLA tracks we're importing for this set.
		retarget_helpers.delete_all_nla_tracks_on_armature(target_rig)

		for filepath in fbx_filepaths:
			base_file_name = os.path.splitext(os.path.basename(filepath))[0]
			anim_name = base_file_name
			if export_set.should_loop(filepath):
				anim_name += '-loop'
			retarget_helpers.push_fbx_animation_to_target_rig_nla_track(filepath, anim_name)

		if not os.path.exists(bpy.context.scene.retarget_batcher_export_path):
			self.report({'ERROR'}, f'Export path not specified.')
			return {'CANCELLED'}

		full_export_path = os.path.join(bpy.context.scene.retarget_batcher_export_path, export_set.export_name + '.glb')

		bpy.ops.export_scene.gltf(
			filepath=full_export_path,
			export_format='GLB',
			export_animation_mode='NLA_TRACKS',
			export_materials='NONE',
			export_reset_pose_bones=True
		) 
		
		print("Purge unused data...")
		bpy.ops.outliner.orphans_purge()

		self.report({'INFO'}, f'Exports finished.')
		return {'FINISHED'}


class VIEW3D_PT_retargetbatcher_via_arp(bpy.types.Panel):
		bl_space_type = 'VIEW_3D'
		bl_region_type = 'UI'
		bl_category = 'Retarget Batcher via ARP'
		bl_label = 'Retarget Batcher via ARP'

		def draw(self, context):
			layout = self.layout

			row = layout.row()
			row.label(text='Import Path')
			row = layout.row()
			row.prop(context.scene, 'retarget_batcher_import_path', text='')

			row = layout.row()
			row.label(text='Export Path')
			row = layout.row()
			row.prop(context.scene, 'retarget_batcher_export_path', text='')

			row = layout.row()
			row.label(text='Export Set Name')
			row = layout.row()
			row.prop(context.scene, 'retarget_batcher_export_set_name', text='')

			row = layout.row()
			layout.operator('retargetbatcher_via_arp.retarget')


classes = [SCENE_OP_retarget_batcher, VIEW3D_PT_retargetbatcher_via_arp]

def register():
	bpy.types.Scene.retarget_batcher_import_path = bpy.props.StringProperty(
		name = 'Import Path',
		description="Choose a directory for animations.",
		default='',
		subtype='DIR_PATH')

	bpy.types.Scene.retarget_batcher_export_path = bpy.props.StringProperty(
		name = 'Export Path',
		description='Choose a directory for exports.',
		default='',
		subtype='DIR_PATH')
	
	bpy.types.Scene.retarget_batcher_export_set_name = bpy.props.StringProperty(
		name = 'Export Set Name',
		description='Name for exported file.',
		default='')

	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

	del bpy.types.Scene.retarget_batcher_export_set_name
	del bpy.types.Scene.retarget_batcher_export_path
	del bpy.types.Scene.retarget_batcher_import_path
