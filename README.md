This is a project which Amy Zhang, Catherine Chen, and Nikhil Raghuraman at Stanford University are working on to
create a wall-mounted light display which reacts to music.

When complete, this project will feature multiple detachable and movable triangular nodes. Each
triangle will light up with a different color whose intensity changes according to the intensity of either bass, midrange,
or treble tones in music.

All code is still a work in progress. Currently, this repository contains code which dissects
a microphone signal into its different frequencies and uses these frequencies to color lights according to music.
It also contains an implementation of a web server (which still needs to be refined) which will be used to transmit information
wirelessly to different nodes of the display.

Different nodes in this display will be controlled by SAM32s (https://github.com/maholli/SAM32).

This project was originally inspired by the Nanoleaf. Visit here for a demo of the original Nanoleaf:
https://www.youtube.com/watch?v=Ynl_XtqQWCQ
