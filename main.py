import os
import fnmatch
from maya import cmds

def clean_ass_files_ui():
    """
    Creates a simple UI to pick a directory, find .ass files, and remove:
      - Lines containing 'specular _<something>_specular_file.r'
      - Entire 'image {...}' blocks with name matching '_<something>_specular_file'
    """
    # If window exists, delete it
    if cmds.window("CleanAssFilesWindow", exists=True):
        cmds.deleteUI("CleanAssFilesWindow")
        
    # Create a new window
    window = cmds.window("CleanAssFilesWindow", title="Clean .ass Files", widthHeight=(400, 220), sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    
    # Folder path row
    cmds.text(label="Select Folder Containing .ass Files:")
    folder_path_field = cmds.textFieldButtonGrp(
        label='Folder Path',
        text='',
        buttonLabel='Browse',
        buttonCommand=lambda: browse_and_set_path(folder_path_field),
        columnAlign=(1, 'left'),
        columnWidth=[(1, 80), (2, 200), (3, 50)]
    )
    
    # Info field: how many .ass files found
    info_text_field = cmds.text(label='No folder selected yet.', align='left')
    
    # Progress bar
    progress_control = cmds.progressBar(maxValue=100, width=300)
    
    # Button to scan and update info
    cmds.button(label="Scan Folder", command=lambda x: scan_folder_for_ass(folder_path_field, info_text_field))
    
    # Execute button
    cmds.button(label="Execute Cleanup", command=lambda x: execute_cleanup(folder_path_field, info_text_field, progress_control))
    
    cmds.setParent('..')
    cmds.showWindow(window)


def browse_and_set_path(folder_path_field):
    """
    Lets the user pick a folder from a file dialog and sets the textField to that path.
    """
    selected_path = cmds.fileDialog2(dialogStyle=2, fileMode=3, caption="Select Folder")
    if selected_path:
        cmds.textFieldButtonGrp(folder_path_field, edit=True, text=selected_path[0])


def scan_folder_for_ass(folder_path_field, info_text_field):
    """
    Scan the chosen folder (including subfolders) for .ass files and update info field with count.
    """
    folder_path = cmds.textFieldButtonGrp(folder_path_field, query=True, text=True)
    if not folder_path or not os.path.isdir(folder_path):
        cmds.warning("Please select a valid folder.")
        cmds.text(info_text_field, edit=True, label="Invalid folder selected.")
        return
    
    all_ass_files = get_ass_files_in_directory(folder_path)
    cmds.text(info_text_field, edit=True, label="Found {} .ass files.".format(len(all_ass_files)))


def execute_cleanup(folder_path_field, info_text_field, progress_control):
    """
    Perform the cleanup of .ass files (remove specular line + entire specular image block),
    while updating the progress bar.
    """
    folder_path = cmds.textFieldButtonGrp(folder_path_field, query=True, text=True)
    if not folder_path or not os.path.isdir(folder_path):
        cmds.warning("Please select a valid folder.")
        return
    
    all_ass_files = get_ass_files_in_directory(folder_path)
    total_files = len(all_ass_files)
    if total_files == 0:
        cmds.text(info_text_field, edit=True, label="No .ass files found to process.")
        cmds.warning("No .ass files found to process.")
        return
    
    # Update UI about the process start
    cmds.text(info_text_field, edit=True, label="Processing {} .ass files...".format(total_files))
    cmds.progressBar(progress_control, edit=True, minValue=0, maxValue=total_files, progress=0)
    
    # Process each .ass file
    for i, ass_file in enumerate(all_ass_files, start=1):
        process_ass_file(ass_file)
        
        # Update progress bar
        cmds.progressBar(progress_control, edit=True, step=1)
    
    # Done
    cmds.text(info_text_field, edit=True, label="Cleanup complete! Processed {} .ass files.".format(total_files))


def get_ass_files_in_directory(folder_path):
    """
    Recursively find all .ass files in the given directory and subdirectories.
    Returns a list of absolute file paths.
    """
    ass_files = []
    for root, dirs, files in os.walk(folder_path):
        for filename in fnmatch.filter(files, '*.ass'):
            ass_files.append(os.path.join(root, filename))
    return ass_files


def process_ass_file(ass_file):
    """
    Read the .ass file line-by-line and rewrite it excluding:
      - The line containing ' specular _RANDOMASSETNAME_specular_file.r'
      - The entire block of 'image { ... }' if it references
        a 'name' containing '_RANDOMASSETNAME_specular_file'.
    """
    # We'll write to a temporary file, then rename it back to original
    temp_file = ass_file + ".tmp"
    
    inside_image_block = False
    lines_in_block = []
    skip_this_block = False
    
    # Helper flags for capturing the block
    with open(ass_file, 'r', encoding='utf-8') as fin, open(temp_file, 'w', encoding='utf-8') as fout:
        for line in fin:
            # 1) Remove line with specular reference (simple substring check)
            #    e.g. " specular _RANDOMASSETNAME_specular_file.r"
            if " specular " in line and "_specular_file.r" in line:
                # Skip this line entirely
                continue
            
            # Check if we are starting an image block
            if not inside_image_block:
                # Look for line that starts an image block
                if line.strip().startswith("image"):
                    inside_image_block = True
                    lines_in_block = [line]
                    skip_this_block = False
                else:
                    # Not an image block, write line as is
                    fout.write(line)
            else:
                # We are inside an image block
                lines_in_block.append(line)
                
                # If this line has 'name' with specular_file
                if "name " in line and "_specular_file" in line:
                    skip_this_block = True
                
                # If we reach the end of the image block
                if line.strip().startswith("}"):
                    # Decide if we skip or keep the block
                    if not skip_this_block:
                        # Write all captured block lines to file
                        for blk_line in lines_in_block:
                            fout.write(blk_line)
                    
                    # Reset flags
                    inside_image_block = False
                    lines_in_block = []
                    skip_this_block = False
    
    # Replace original file with cleaned file
    os.remove(ass_file)
    os.rename(temp_file, ass_file)


# To launch the UI, simply call:
clean_ass_files_ui()
