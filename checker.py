from __future__ import print_function

import os.path
import functools
from itertools import islice
from collections import namedtuple

import click

from p4t.simple.classifiers import ClassifierFactory
import p4t.optimizations.lpm as lpm_opt

import parsing


GlobalParams = namedtuple('GlobalParams', ['max_entries', 'output_file'])
PARAMS = None

OIParams = namedtuple('OIParams', ['algo', 'cutoff', 'bit_width', 'only_exact'])
OI_PARAMS = None

LPMParams = namedtuple('LPMParams', ['max_groups', 'max_memory'])
LPM_PARAMS = None

def add_row(kind, filename, num_entries, oi_algorithm, bit_width, max_groups, num_groups, num_entries_traditional, groups, max_memory, expanded_groups):
    with open(PARAMS.output_file, 'a') as f:
        print(kind, filename, PARAMS.max_entries, num_entries, oi_algorithm, bit_width,
              max_groups, num_groups, num_entries_traditional, sorted(groups, reverse=True) if groups is not None  else None,
              max_memory, sorted(expanded_groups, reverse=True) if expanded_groups is not None else None, sep='\t', file=f)


def read_classifier(filename):
    with open(filename, 'r') as input_file:
        classifier = parsing.read_classifier(
            parsing.classbench_expanded,
            islice(input_file, 0, PARAMS.max_entries)
        )
    return classifier


@click.group()
@click.option('--max-entries', default=None, help='Number of entries to take from the input', type=int)
@click.option('--output_file', default='data.tsv', help='File to store')
@click.option('--num-threads', default=None, help='Number of threads to use', type=int)
@click.option('--oi-cutoff', default=100, help='Maximal allowed number of groups in any OI invocation', type=int)
@click.option('--algo', default='icnp_blockers', help='OI algorithm to use', type=str)
@click.option('--bit-width', default=32, help='Required bit width', type=int)
@click.option('--only-exact', help='Use only exact bits?', is_flag=True)
@click.option('--max-groups', default=None, help='Maximal allowed number of groups', type=int)
@click.option('--max-memory', default=None, help='Maximal number of entries', type=int)
def greet(max_entries, output_file, num_threads, oi_cutoff, algo, bit_width, only_exact, max_groups, max_memory):
    global PARAMS  # pylint: disable=global-statement
    PARAMS = GlobalParams(max_entries=max_entries, output_file=output_file)
    global OI_PARAMS
    OI_PARAMS = OIParams(cutoff=oi_cutoff, algo=str(algo), only_exact=only_exact, bit_width=bit_width)
    global LPM_PARAMS
    LPM_PARAMS = LPMParams(max_groups=max_groups, max_memory=max_memory)

    if num_threads is not None:
        lpm_opt.set_number_of_threads(num_threads)

    print('Hey, we are gonna test some algos!!')


def do_optimize_oi(input_files, oi_params):
    kind = 'oi' if not oi_params.only_exact else 'oi_exact'

    for input_file in input_files:
        print("performing {:s} on {:s}: bitwidth = {:d}, algo = {:s}".format(
            kind, os.path.basename(input_file), oi_params.bit_width, oi_params.algo
            ))
        classifier = read_classifier(input_file)

        subclassifiers, traditional = lpm_opt.optimize_oi(
            classifier, ClassifierFactory(), oi_params.bit_width,
            oi_params.algo, oi_params.only_exact, oi_params.cutoff)

        add_row(kind, os.path.basename(input_file), len(classifier), oi_params.algo,
                oi_params.bit_width, None, len(subclassifiers), len(traditional),
                [len(s) for s in subclassifiers], None, None)


def do_optimize_oi_lpm(input_files, oi_params, lpm_params):
    kind = 'oi_lpm'
    assert(lpm_params.max_groups is None or lpm_params.max_memory is None)
    if lpm_params.max_groups is not None:
        kind += "_bounded"
    if lpm_params.max_memory is not None:
        kind += "_memory_bounded"

    for input_file in input_files:
        print("performing {:s} on {:s}: bitwidth = {:d}, algo = {:s}{:s}{:s}".format(
            kind, os.path.basename(input_file), oi_params.bit_width, oi_params.algo,
            "" if lpm_params.max_groups is None else ', max_groups = {:d}'.format(lpm_params.max_groups),
            "" if lpm_params.max_memory is None else ', max_memory = {:d}'.format(lpm_params.max_memory)
            ))

        classifier = read_classifier(input_file)

        subclassifiers, oi_traditional = lpm_opt.optimize_oi(
            classifier, ClassifierFactory(), oi_params.bit_width, oi_params.algo, False, oi_params.cutoff)

        all_group_sizes = []

        if lpm_params.max_groups is not None:
            subclassifiers, traditionals = lpm_opt.optimize_bounded(subclassifiers, ClassifierFactory(), lpm_params.max_groups)

            add_row(kind, os.path.basename(input_file), len(classifier), oi_params.algo,
                    oi_params.bit_width, lpm_params.max_groups, len(subclassifiers), 
                    len(oi_traditional) + sum(len(x) for x in traditionals), [len(s) for s in subclassifiers],
                    None, None)
        elif lpm_params.max_memory is not None:
            subclassifiers, nexp_subclassifiers = lpm_opt.optimize_lpm_bounded_memory(subclassifiers, ClassifierFactory(), lpm_params.max_memory)
            add_row(kind, os.path.basename(input_file), len(classifier), oi_params.algo,
                    oi_params.bit_width, None, len(subclassifiers), len(oi_traditional), [len(s) for s in nexp_subclassifiers],
                    lpm_params.max_memory, [len(s) for s in subclassifiers])
        else:
            for subclassifier in subclassifiers:
                mgc = lpm_opt.optimize(subclassifier, ClassifierFactory())
                all_group_sizes.extend(len(s) for s in mgc)

            add_row(kind, os.path.basename(input_file), len(classifier), oi_params.algo,
                    oi_params.bit_width, None, len(all_group_sizes), len(oi_traditional), all_group_sizes,
                    None, None)


def do_optimize_lpm(input_files, lpm_params):
    kind = 'lpm' if lpm_params.max_groups is None else 'lpm_bounded'
    for input_file in input_files:
        print("performing lpm on {:s}{:s}".format(
            os.path.basename(input_file), ": max_groups = {:d}".format(lpm_params.max_groups)
            ))

        classifier = read_classifier(input_file)

        if lpm_params.max_groups is not None:
            subclassifiers, traditionals = lpm_opt.optimize_bounded([classifier], ClassifierFactory(), lpm_params.max_groups)
        else:
            subclassifiers, traditionals = lpm_opt.optimize(classifier, ClassifierFactory()), []

        add_row(kind, os.path.basename(input_file), len(classifier), 'NA',
                classifier.bitwidth, None, len(subclassifiers), sum(len(x) for x in traditionals), 
                [len(s) for s in subclassifiers])


def do_optimize_lpm_oi(input_files, oi_params):
    for input_file in input_files:
        print("performing lpm_oi on {:s}: bitwidth = {:d}, algo = {:s}".format(
            os.path.basename(input_file), oi_params.bit_width, oi_params.algo,
            ))

        classifier = read_classifier(input_file)

        mgc = lpm_opt.optimize(classifier, ClassifierFactory())

        all_group_sizes = []
        size_traditional = 0
        for pr_classifier in mgc:
            subclassifiers, traditional = lpm_opt.optimize_oi(
                pr_classifier, ClassifierFactory(), oi_params.bit_width,
                oi_params.algo, False, oi_params.oi_cutoff)
            all_group_sizes.extend(len(sc) for sc in subclassifiers)
            size_traditional += len(traditional)

        add_row('lpm_oi', os.path.basename(input_file), len(classifier), oi_params.algo,
                oi_params.bit_width, None, len(all_group_sizes), size_traditional, all_group_sizes)


@greet.command()
@click.argument('input_files', nargs=-1)
def optimize_oi(input_files):
    do_optimize_oi(input_files, OI_PARAMS)


@greet.command()
@click.argument('input_files', nargs=-1)
def optimize_oi_lpm(input_files):
    do_optimize_oi_lpm(input_files, OI_PARAMS, LPM_PARAMS)


@greet.command()
@click.argument('input_files', nargs=-1)
def optimize_lpm(input_files):
    do_optimize_lpm(input_files, LPM_PARAMS)


@greet.command()
@click.argument('input_files', nargs=-1)
def optimize_lpm_oi(input_files):
    do_optimize_lpm_oi(input_files, OI_PARAMS)


@greet.command()
@click.argument('input_files', nargs=-1)
@click.option('--bit-width', help='Required bit width', type=int, multiple=True)
@click.option('--max-groups', help='Maximal allowed number of groups', type=int, multiple=True)
@click.option('--max-memory', help='Maximal allowed number of entries', type=int, multiple=True)
@click.option('--without-oi-lpm', help='Disable OI calculation', is_flag=True)
@click.option('--without-lpm-bounded', help='Disable lpm bounded calculation', is_flag=True)
@click.option('--without-oi-lpm-memory-bounded', help='Disable OI LPM memory bounded calculation', is_flag=True)
def optimize_for_paper(input_files, bit_width, max_groups, max_memory, without_oi_lpm, without_lpm_bounded, without_oi_lpm_memory_bounded):
    if not without_lpm_bounded:
        for mg in max_groups:
            do_optimize_lpm(input_files, LPM_PARAMS._replace(max_groups=mg))
    for bw in bit_width:
        if not without_oi_lpm:
            do_optimize_oi_lpm(input_files, OI_PARAMS._replace(bit_width=bw), LPM_PARAMS)
        if not without_oi_lpm_memory_bounded:
            for mm in max_memory:
                do_optimize_oi_lpm(input_files, OI_PARAMS._replace(bit_width=bw), LPM_PARAMS._replace(max_memory=mm))


if __name__ == '__main__':
    greet()
