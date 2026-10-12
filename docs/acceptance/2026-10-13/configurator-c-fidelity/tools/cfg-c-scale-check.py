#!/usr/bin/env python3
"""Measure a comparison sheet against the runtime boxes it claims, with PIL.

    python3 tools/cfg-c-scale-check.py <cmp-name>.png [measurements.json]

`measurements.json` (written by tools/cfg-c-fidelity.mjs next to it) records,
for every sheet, where each panel sits in the PNG and which image rows that
panel shows. This script reads those records, predicts where a card's borders
must fall if the sheet is 1 image pixel per CSS pixel, finds the border rows
and columns in the pixels, and prints measured vs predicted for both panels.

Both panels of a sheet are crops of full-page screenshots taken at
deviceScaleFactor 1, so a card measured on one panel is directly comparable
with a card measured on the other; a ratio of 1.00 for both is what proves the
sheets do not rescale anything (the review of the first round found the app
panel at 1.16x, from a sheet that stretched a 1240px element screenshot to
1440px).
"""
import json
import os
import sys

from PIL import Image

BORDER = (223, 231, 236)


def is_border( pixel ):
    return all( abs( pixel[ i ] - BORDER[ i ] ) <= 6 for i in range( 3 ) )


def border_row( img, x, y, window ):
    """The row near y that carries the most card-border pixels along x."""
    best, best_y = -1, None
    for row in range( y - window, y + window + 1 ):
        count = sum(
            1 for xx in range( x[ 0 ], x[ 1 ], 4 ) if is_border( img.getpixel( ( xx, row ) ) )
        )
        if count > best:
            best, best_y = count, row
    return best_y, best


def main():
    png = sys.argv[ 1 ]
    here = os.path.dirname( os.path.abspath( __file__ ) )
    measurements = (
        sys.argv[ 2 ]
        if len( sys.argv ) > 2
        else os.path.join( os.path.dirname( here ), 'measurements.json' )
    )
    data = json.load( open( measurements ) )
    name = os.path.basename( png )[ len( 'cmp-' ) : -len( '.png' ) ]
    sheet = data[ 'sheets' ][ name ]
    label = name.split( '-' )[ 0 ]
    sides = [ 'proto', 'prod-' + name.split( '-' )[ 1 ] ]
    img = Image.open( png ).convert( 'RGB' )
    print( png, 'image', img.size )
    for panel, side in zip( sheet[ 'panels' ], sides ):
        box = data[ f'{ side }-{ label }' ][ 'card' ][ 'box' ]
        top = panel[ 'y' ] + ( box[ 1 ] - panel[ 'from' ][ 1 ] )
        left = panel[ 'x' ] + ( box[ 0 ] - panel[ 'from' ][ 0 ] )
        right = left + box[ 2 ]
        span_x = ( left + 6, right - 6 )
        found_top, hits_top = border_row( img, span_x, top, 4 )
        found_bottom, hits_bottom = border_row(
            img, span_x, top + box[ 3 ], 4
        )
        middle = ( found_top + found_bottom ) // 2
        columns = [
            xx
            for xx in range( left - 4, right + 5 )
            if is_border( img.getpixel( ( xx, middle ) ) )
        ]
        print(
            f"  {side:8s} {panel[ 'src' ].split( '/' )[ -1 ] }:"
            f" predicted rows {top}..{top + box[ 3 ]}, found {found_top}..{found_bottom }"
            f" (border pixels {hits_top}, {hits_bottom});"
            f" height {found_bottom - found_top} px vs runtime {box[ 3 ] }"
            f" ({( found_bottom - found_top ) / box[ 3 ]:.4f}x);"
            f" borders at columns {columns[ 0 ]}..{columns[ -1 ] }"
            f" -> width {columns[ -1 ] - columns[ 0 ]} px vs runtime {box[ 2 ]}"
            f" ({( columns[ -1 ] - columns[ 0 ] ) / box[ 2 ]:.4f}x)"
        )


if __name__ == '__main__':
    main()
