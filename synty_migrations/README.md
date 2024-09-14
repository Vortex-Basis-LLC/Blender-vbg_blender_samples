NOTE: This is initial work towards converting Synty animations into a form usable in Godot.
- Still work to do!


- Ensure you have Synty Locomotion and/or Sword Animation pack imported into Unity (or extract unitypackage into a folder).

- Go to Scripting tab and select “SyntyAnimToGLB”.
  - Update “base_synty_animation_path” value to the folder containing AnimationBaseLocomotion and AnimationSwordCombat on your machine.
  - Set “export_path” to the folder where you want the GLB files to be generated.

- If you want a character model bound to your animations, replace “Armature” object in the blend file with one of your choosing that has same bone structure and names as the Synty characters.

- Open the System Console (from “Window” / “Toggle System Console”) to see output from the script.

- Run “SyntyAnimToGLB” from Scripting tab to generate all of the GLB files.
  - One GLB file will be created for each entry in “export_sets”. I had to split them up into separate GLB files because Godot would crash if I had too many animations in one GLB file.

- Wait about 5 minutes for script to finish (depends on speed of your machine).

- In Godot, drag and drop the GLB files into the project FileSystem.

- Select each GLB file and on the Import tab:
  - Change “Import As” to “Animation Library”
  - Check “Import as Skeleton Bones” if no model is bound to the target armature used in Blender.
  - Check the “Trimming” checkbox.
  - Click “Reimport”.
  - Double-click on the GLB file and update the Bone Map.
  - three_finger_synty_bone_map.tres is an example bonemap provided in the GitHub rep.
  - Click “Reimport”.

- You should now be able to use the Synty animations with humanoid characters in Godot.