import json

from cerebras.sdk.client import SdkCompiler # pylint: disable=import-error,no-name-in-module

hash_filename = "hash.json"

with SdkCompiler() as compiler:
  hashstr = compiler.compile(
      "./src",
      "layout_matvec.csl",
      "--arch wse3 --fabric-dims=9,4 --fabric-offsets=4,1 "
      "--params=width:2,height:2,tile_size:25,iters:1 -o latest --memcpy --channels=1",
  )
  
  print("compile artifact:", hashstr)
  
  print(f"dump artifact name to file {hash_filename}")
  with open(hash_filename, "w", encoding="utf-8") as write_file:
    json.dump(hashstr, write_file)
