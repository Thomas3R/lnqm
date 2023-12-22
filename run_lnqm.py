try:
    from lnqm import LnQM_Dataset
    import subprocess
    import os
    import numpy as np
except ModuleNotFoundError:
    print()
    print('Did you: conda activate lnqm ?')
    print()
    quit()

# functions for running GFN-FF calculations
def run_gfnff(xtbver):
    # Check if the "coord" file exists in the current directory
    if not os.path.isfile("coord"):
        return None, "Error: 'coord' file not found in the current directory"

    # Check if the "gfnff_topo" file exists and remove it
    if os.path.isfile("gfnff_topo"):
        os.remove("gfnff_topo")
    try:
        flags=" coord --gfnff --opt --dipole"
        #command = xtbver + flags
        # Run the binary and capture both stdout and stderr
        result = subprocess.run(
            ["%s" % xtbver, "coord", "--gfnff", "--opt", "--dipole"],
            #["ls", "-l"],
            #["%s" % xtbver, "%s" % flags],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # Set to True for text output, False for binary
        )

        # Check if the process was successful (return code 0)
        if result.returncode == 0:
            return result.stdout, 0  # Successful, return stdout and no stderr
        else:
            return result.stdout, result.stderr  # Failed, return no stdout and stderr

    except Exception as e:
        return None, str(e)  # Return error message if an exception occurs


def get_directory_starting_with(prefix):
    try:
        # Get the list of items (files and directories) in the current directory
        items = os.listdir()

        # Use list comprehension to filter directories that start with the specified prefix
        matching_directories = [item for item in items if os.path.isdir(item) and item.startswith(prefix)]

        if len(matching_directories) == 1:
            return matching_directories[0]  # Return the first and only match
        elif len(matching_directories) > 1:
            print(f"Error: Multiple directories starting with '{prefix}' found.")
            return None
        else:
            print(f"Error: No directory starting with '{prefix}' found.")
            return None

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def change_dir(relative_path, split_uid):
    try:
        # Get the current working directory
        current_directory = os.getcwd()

        # Construct the absolute path by joining the current directory with the relative path
        new_directory = os.path.join(current_directory, relative_path)

        # Check if the path exists before attempting to change the working directory
        if os.path.exists(new_directory):
            # Change the working directory to the new path
            os.chdir(new_directory)
            print(f"Changed working directory to: {new_directory}")
            calc_dir=get_directory_starting_with(split_uid)
            os.chdir(calc_dir)
            print(f"Changed working directory to: {calc_dir}")
        else:
            print(f"Error: Path '{new_directory}' does not exist.")

    except Exception as e:
        print(f"Error: {str(e)}")



# load LnQM from disk
dataset = LnQM_Dataset(path_to_hdf5="lnqm.h5")

# interesting features
fi = list()
fi.append("numbers")
fi.append("cn")
fi.append("coord")
fi.append("hirshfeld_charges")
fi.append("eeq")
fi.append("energy_geoopt")
fi.append("gradient")
fi.append("dipole")

# fake periodic table
sym=list()
for i in range(86):
    sym.append("")
sym[1]="H"
sym[57]="La"
sym[58]="Ce"
sym[59]="Pr"
sym[60]="Nd"
sym[61]="Pm"
sym[62]="Sm"
sym[63]="Eu"
sym[64]="Gd"
sym[65]="Tb"
sym[66]="Dy"
sym[67]="Ho"
sym[68]="Er"
sym[69]="Tm"
sym[70]="Yb"
sym[71]="Lu"

# list with number of calcs done for each element
ncalc=np.zeros(86)
# limit number of calculations per atom type to max_calc
max_calc=1

# save base directory to change back to
base_dir=os.getcwd()

# which xtb version to use
xtbver="xtb_highcn"

# loop over each sample in the dataset
i=0
for data in dataset:
    # print features
    at=int(data[fi[0]][0])
    if ncalc[at] >= max_calc:
        continue
    cn=float(data[fi[1]][0])
    print("")
    print("UID:",data.uid)
    print('Atom type of first atom:', at)
    print('CN of first atom: %6.2f' % cn)
    
    # start GFN-FF calculations for the samples
    at_dir=sym[at]
    uid_split=str(data.uid).split("_")[0]
    path="_geometries/lnqm_geometries/geometries/"+at_dir+"/"
    change_dir(path, uid_split)

    # run the GFN-FF calculation
    stdout, stderr = run_gfnff(xtbver)
    
    # evaluate the output
    print('Std-error:',stderr)
    lines=stdout.splitlines()

    # evaluate start vs optimized energies
    energy_line=[line for line in lines if ":: total energy " in line]
    if len(energy_line) == 2:
        earr=np.zeros(2)
        i=0
        for line in energy_line:
            cline=" ".join(line.split())
            e=cline.split(" ")[3]
            earr[i]=e
            i+=1
        dE_opt=earr[1]-earr[0]
        print('Energy difference between start and end in Eh:')
        print('dE(opt)=',dE_opt)
        if dE_opt >= 0.0:
            print('WARNING: dE(opt) is bigger than zero!')
            print('  optimization increased the energy :(')

    # further cleanup of created files in the calculation folder
    if os.path.isfile("gfnff_charges"):
        os.remove("gfnff_charges")
    if os.path.isfile("gfnff_topo"):
        os.remove("gfnff_topo")
    #if os.path.isfile("xtbopt.log"):
    #    os.remove("xtbopt.log")
    if os.path.isfile("xtbopt.coord"):
        os.remove("xtbopt.coord")


    # go back to base directory
    os.chdir(base_dir)
    
    # increase number of done calculations by one for atom type
    ncalc[at] = ncalc[at] + 1
    # for now quit after one calc per at
    if sum(ncalc) == 14:
        print()
        print('Done 1 calc for each element.')
        quit()
