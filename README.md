# codestream-parser

**all-JPEG Codestream/File Format Parser Tools**

This archive contains a set of Python scripts that can be used to parse
JPEG, JPEG 2000, JPEG XR, JPEG XS and JPEG XT files and output
their contents.

* ```jp2codestream.py```

  Codestream parsing for JPEG 2000 parsing. Call this script with a 
  raw codestream as argument to parse it. The overhead output at the 
  end denotes the number of paket header bytes, i.e. the size of 
  data that is not directly used for image data.

* ```jp2file.py```

  JPEG 2000 File Format parsing. Call this script with a JPEG 2000 file
  as argument to parse it and its codestream. This is a generic jpx
  container parser that is also aware of JPEG XR with ISO boxes and
  the JPEG XS file format. Additionally supported flags:

    ```-C```, ```--ignore-codestream```: Don't parse the Codestream boxes.

* ```jp2box.py```

  JPEG 2000 File Format box parsing. This is used by jp2file.py.

* ```jp2utils.py```

  Some helper functions used by the other scripts.

* ```jxrfile.py```

  JPEG XR file format and codestream parsing. This is a combined
  parser for both formats. Uses jp2utils and icc.

* ```jpgcodestream.py```

  Codestream parsing for ISO/IEC 10918-1 and ISO/IEC 18477-3 (JPEG and
  JPEG XT).

* ```jxscodestream.py```

  Codestream parsing for ISO/IEC 21122-1 (JPEG XS)

* ```jpgxtbox.py```

  Some helper functions for JPEG XT box parsing.
  

Please contact Thomas Richter <thomas.richter@iis.fraunhofer.de>
for comments and suggestions.
