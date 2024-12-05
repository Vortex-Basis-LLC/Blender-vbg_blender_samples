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
from . import anim_file_crawler

AnimFileCrawler = anim_file_crawler.AnimFileCrawler

class SCENE_OP_synty_rest_reset(bpy.types.Operator):
	"""Retarget a series of animations onto a target rig."""

	bl_idname = 'rest_reset_synty_via_arp.retarget'
	bl_label = 'Batch Reset Rest Poses'
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

		if not os.path.exists(bpy.context.scene.synty_anim_import_path):
			self.report({'ERROR'}, 'Import path not specified.')
			return {'CANCELLED'}
		
		if not os.path.exists(bpy.context.scene.synty_anim_export_path):
			self.report({'ERROR'}, f'Export path not specified.')
			return {'CANCELLED'}

		export_set = AnimFileCrawler(
			os.path.join(bpy.context.scene.synty_anim_import_path),
			loop = True
		)

		anim_entries = []
		export_set.crawl_folders_for_anims(export_set.root_path, anim_entries)

		target_rig_name = scene.target_rig
		target_rig = scene.objects[target_rig_name]

		# Clear current NLA tracks, so that we only have the new NLA tracks we're importing for this set.
		retarget_helpers.delete_all_nla_tracks_on_armature(target_rig)

		for anim_entry in anim_entries:
			rel_path = anim_entry.relative_path
			full_path = anim_entry.full_path
			out_path = os.path.join(bpy.context.scene.synty_anim_export_path, rel_path)

			retarget_helpers.reset_fbx_animation_rest_pose_and_export(full_path, out_path)

		
		print("Purge unused data...")
		bpy.ops.outliner.orphans_purge()

		self.report({'INFO'}, f'Exports finished.')
		return {'FINISHED'}


class VIEW3D_PT_rest_reset_synty_via_arp(bpy.types.Panel):
		bl_space_type = 'VIEW_3D'
		bl_region_type = 'UI'
		bl_category = 'Rest Reset Synty via ARP'
		bl_label = 'Rest Reset Synty via ARP'

		def draw(self, context):
			layout = self.layout

			row = layout.row()
			row.label(text='Synty Import Path')
			row = layout.row()
			row.prop(context.scene, 'synty_anim_import_path', text='')

			row = layout.row()
			row.label(text='Synty Export Path')
			row = layout.row()
			row.prop(context.scene, 'synty_anim_export_path', text='')

			row = layout.row()
			layout.operator('rest_reset_synty_via_arp.retarget')


classes = [SCENE_OP_synty_rest_reset, VIEW3D_PT_rest_reset_synty_via_arp]

def register():
	bpy.types.Scene.synty_anim_import_path = bpy.props.StringProperty(
		name = 'Synty Anim Root Path',
		description="Choose the root directory for Synty animations.",
		default='',
		subtype='DIR_PATH')

	bpy.types.Scene.synty_anim_export_path = bpy.props.StringProperty(
		name = 'Synty Anim Export Path',
		description='Choose a directory for exports.',
		default='',
		subtype='DIR_PATH')

	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

	del bpy.types.Scene.synty_anim_export_path
	del bpy.types.Scene.synty_anim_import_path
