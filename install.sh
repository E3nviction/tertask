#!/usr/bin/env bash

# Create a file that runs a python file using this absolute path
echo "#!/usr/bin/env bash" > tertask
echo "python3 $(pwd)/main.py" >> tertask
chmod +x tertask
echo "Move the 'tertask' file to any folder that is accessible from \$PATH"