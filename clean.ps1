#
# Clean up build artifacts from the Python build and setuptools modules
#

# Change the directory where this script lives; exit on error
Push-Location $(Split-Path -Path $MyInvocation.MyCommand.Definition -Parent) -ErrorAction Stop

# Remove build artifacts
Remove-Item -Recurse -Force build, dist, *.egg-info -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
