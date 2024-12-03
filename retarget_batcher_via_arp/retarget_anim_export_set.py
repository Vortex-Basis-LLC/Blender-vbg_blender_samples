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


class RetargetAnimExportSet:
	export_name = ''
	root_path = ''
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


	def crawl_folders_for_anims(self, folder_path, out_filepaths):
		path_contents = os.listdir(folder_path)
		for filename in path_contents:
			filename_lower = filename.lower()
			
			full_path = os.path.join(folder_path, filename)
			if os.path.isdir(full_path):
				self.crawl_folders_for_anims(full_path, out_filepaths)
			elif filename_lower.endswith('.fbx'):
				include = True
				
				if self.filename_must_have is not None:
					if self.filename_must_have.lower() not in filename_lower:
						include = False
						
				if self.filename_must_not_have is not None:
					if self.filename_must_not_have.lower() in filename_lower:
						include = False
				
				if include:
					out_filepaths.append(full_path)


	def should_loop(self, filepath):
		# TODO: Add way to specify rule list or overrides...
		basename = os.path.basename(filepath).lower()
		if '_to_' in basename:
			return False
		if 'jump' in basename:
			return False

		if 'walk' in basename:
			return True
		if 'sprint' in basename:
			return True
		if 'shuffle' in basename:
			return True
		if 'turn' in basename:
			return True
		if 'idle' in basename:
			return True
		
		return False
