# Sigcomm 2017 LPM


## Prerequisites:

 1. Prerequisites for [sigcomm2017lpmP4](https://github.com/sigcomm2017submission/sigcomm2017lpmP4)
 2. [Python 2.7](https://www.python.org/)
 3. [click](http://click.pocoo.org/5/) python package

## Steps to reproduce:

 1. Clone [sigcomm2017lpm_p4](https://github.com/sigcomm2017submission/sigcomm2017lpm_p4) and [sigcomm2017lpm](https://github.com/sigcomm2017submission/sigcomm2017lpm) repositories into the same folder.
 2. Follow compilation instructions for [sigcomm2017lpm_p4](https://github.com/sigcomm2017submission/sigcomm2017lpm_p4).
 3. __Switch__ to the `sigcomm2017lpm` folder and execute:

     ```bash
     source setenv.sh
     ```

 4. To calculate Table 1 (l = 16, 24, 32) run:

     ```bash
     python checker.py optimize_for_paper \
         --bit-width 16 --bit-width 24 --bit-width 32 test/*.txt
     ```

 5. To calculate Table 1 (l = 104) run:

     ```bash
     python checker.py optimize_for_paper \
         --max-groups 5 --max-groups 10 --max-groups 20 test/*.txt
     ```

 6. To calculate Table 2 run:

     ```bash
     python checker.py optimize_for_paper \
         --bit-width 16 --bit-width 24 --bit-width 32 \
         --max-memory 100000 --max-memory 1000000 test/*.txt
     ```

All data will be located in `data.tsv`.
