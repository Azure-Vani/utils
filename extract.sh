#!/bin/bash
if [ "$#" \< 1 ]; then exit; fi
tmpdir=/tmp/unzip_gbk
7za x "$1" -o$tmpdir
convmv -f utf-8 -t iso-8859-1 -r $tmpdir --notest
convmv -f gbk -t utf-8 -r $tmpdir --notest
for i in $tmpdir/*;do
        i=${i#*$tmpdir/}
        mv "$tmpdir/$i" "$i"
done
rm -r $tmpdir
