# Retarget Batcher via ARP

NOTE: This tool requires that you already have Auto-Rig Pro installed in Blender.
If you don't have Auto-Rig Pro, you can buy it here (I have no affiliation with
makers of Auto-Rig Pro, but it is a pretty useful tool):
https://blendermarket.com/products/auto-rig-pro

This extensions will reset a set of FBX animations to a common rest pose and export
them in groups to a series of GLB files.

The initial use case for this tool is to fixup Synty's animation libraries and package them
into a format that is easily usable within Godot.

# Instructions (Synty Use Case)

- Install/enable Auto-Rig Pro
- Purchase Synty animation packs and unzip Blender source files under a common directory.
- Start new Blender project
- Import A_TPose_Neut.fbx (under Armature, Enable: Ignore Leaf Bones and Automatic Bone Orientation, Do Not Enable: Force Connect Children).
- Go to Auto-Rig Pro Remap. Set TPose as your source and target armature. Click Build Bone map.
- Import the ARP bonemap from extension folder: synty_remap_preset.bmap
- Go to the N-key viewport tab for "Retarget Batcher via ARP"
- Set "Anim Config CSV" to synty_anim_metadata.csv in extension folder
	- NOTE: This indicates which animation FBX files should be included and how they should be grouped.
	- The provided CSV file has the animations listed for Base Locomotion, Sword Combat, and Idle Synty animations.
	- This also indicates whehter -loop should be appended to the NLA track name so that Godot will loop it by default.
- Set "Import Path" to the root folder that contains all of your Synty FBXs.
- Set "Export Path" to the folder that will receive the generated (anim group).GLB files.
- Click "Batch Retarget".
- Wait a while (10-30 minutes probably depending on speed of your PC)
- Your export path will now contain GLB files usable as animation libraries in Godot.

To use the GLB files in Godot:
- Drag and drop GLB files into your Godot FileSystem.
- Select each GLB file, go to "Import" tab.
	- Change "Import As" to "Animation Library"
	- Check "Trimming", "Remove Immutable Tracks", and "Import Rest as Reset".
	- Click "Reimport"
	- Click "Advanced"
	- Select "Skeleton3D" in scene browser. Create bone map (or use synty_anim_bone_map.tres in extension folder)
	- Click "Reimport"

To add animations to your character:
- With AnimationPlayer for your character selected:
  - In Animation tab, click Animation button then "Manage Animations"
  - Load library and then pick one of the GLB files you imported.