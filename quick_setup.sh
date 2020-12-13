set -e

mkdir -p ~/temp/sym
cd ~/temp/sym

echo "Creating virtual env..."
python3 -m venv venv

echo "Installing symphony..."
./venv/bin/pip install git+ssh://git@github.com/orlevii/symphony.git -U

echo "DONE!"
echo "----"
echo "Usage:"
echo "cd ~/temp/sym"
echo "source ./venv/bin/activate"
echo "symphony_client --host HOST_NAME"
