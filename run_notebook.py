"""Fresh kernel, Run All, save outputs even if a cell fails."""
from pathlib import Path
import sys, os
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

OUT=Path(__file__).parent
os.environ['MPLCONFIGDIR']=str(OUT/'.matplotlib')
os.environ['IPYTHONDIR']=str(OUT/'.ipython')
nb=nbformat.read(OUT/'reconstruction.ipynb',as_version=4)
km=KernelManager(kernel_name='python3')
km.kernel_spec.argv[0]=sys.executable
client=NotebookClient(nb,km=km,timeout=1800,resources={'metadata':{'path':str(OUT)}})
try:
    client.execute()
finally:
    nbformat.write(nb,OUT/'reconstruction.ipynb')
print('Fresh-kernel Run All completed successfully.')
