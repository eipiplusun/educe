#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Eric Kow
# License: BSD3

"""
Extract features to CSV files
"""

from __future__ import print_function
from os import path as fp
import codecs
import os
import sys

from educe.learning.keygroup_vectorizer import (KeyGroupVectorizer)
from educe.stac.annotation import (DIALOGUE_ACTS,
                                   SUBORDINATING_RELATIONS,
                                   COORDINATING_RELATIONS)
from educe.stac.learning import features
import educe.corpus
from educe.learning.edu_input_format import (dump_all,
                                             labels_comment,
                                             dump_svmlight_file,
                                             dump_edu_input_file)
from educe.learning.vocabulary_format import dump_vocabulary
import educe.glozz
import educe.stac
import educe.util

from ..doc_vectorizer import (DialogueActVectorizer,
                              LabelVectorizer)
from ..features import (mk_high_level_dialogues,
                        extract_pair_features,
                        extract_single_features)

NAME = 'extract'


# ----------------------------------------------------------------------
# options
# ----------------------------------------------------------------------


def config_argparser(parser):
    """
    Subcommand flags.
    """
    parser.add_argument('corpus', metavar='DIR',
                        help='Corpus dir (eg. data/pilot)')
    parser.add_argument('resources', metavar='DIR',
                        help='Resource dir (eg. data/resource)')
    parser.add_argument('output', metavar='DIR',
                        help='Output directory')
    # add flags --doc, --subdoc, etc to allow user to filter on these things
    educe.util.add_corpus_filters(parser,
                                  fields=['doc', 'subdoc', 'annotator'])
    parser.add_argument('--verbose', '-v', action='count',
                        default=1)
    parser.add_argument('--quiet', '-q', action='store_const',
                        const=0,
                        dest='verbose')
    parser.add_argument('--window', action='store', metavar='INT', type=int,
                        default=5,
                        help="Ignore EDU pairs greater this distance apart "
                        "(-1 for no window) ")
    parser.add_argument('--single', action='store_true',
                        help="Features for single EDUs (instead of pairs)")
    parser.add_argument('--parsing', action='store_true',
                        help='Extract features for parsing')
    parser.add_argument('--debug', action='store_true',
                        help='Emit fields used for debugging purposes')
    parser.add_argument('--experimental', action='store_true',
                        help='Enable experimental features '
                             '(currently corenlp)')
    parser.add_argument('--ignore-cdus', action='store_true',
                        help='Avoid going into CDUs')
    parser.set_defaults(func=main)

# ---------------------------------------------------------------------
# main
# ---------------------------------------------------------------------


#def main_parsing_pairs(args):
#    """
#    Main to call when live data are passed in (--parsing). Live data are data
#    that we want to discourse parsing on, so we don't know if they are attached
#    or what the label is.
#
#    As of 2014-08-19, there must be an 'unannotated' stage and an optional
#    'units' stage (for dialogue acts)
#    """
#    inputs = features.read_corpus_inputs(args, stage='units|unannotated')
#    features_file = os.path.join(args.output, 'extracted-features.csv')
#    with codecs.open(features_file, 'wb') as ofile:
#        header = features.PairKeys(inputs)
#        writer = mk_csv_writer(header, ofile)
#        feats = features.extract_pair_features(inputs,
#                                               args.window,
#                                               live=True)
#        for row, _ in feats:
#            writer.writerow(row)


def main_corpus_single(args):
    """
    The usual main. Extract feature vectors from the corpus
    (single edus only)
    """
    inputs = features.read_corpus_inputs(args)
    dialogues = list(mk_high_level_dialogues(inputs, args.parsing))
    # these paths should go away once we switch to a proper dumper
    out_file = fp.join(args.output, fp.basename(args.corpus))
    out_file += '.just-edus.sparse'
    instance_generator = lambda x: x.edus[1:]  # drop fake root

    # pylint: disable=invalid-name
    # scikit-convention
    feats = extract_single_features(inputs, live=args.parsing)
    vzer = KeyGroupVectorizer()
    X_gen = vzer.fit_transform(feats)
    # pylint: enable=invalid-name
    labtor = DialogueActVectorizer(instance_generator, DIALOGUE_ACTS)
    y_gen = labtor.transform(dialogues)

    if not fp.exists(args.output):
        os.makedirs(args.output)

    # list dialogue acts
    comment = labels_comment(labtor.labelset_)

    # dump: EDUs, pairings, vectorized pairings with label
    edu_input_file = out_file + '.edu_input'
    dump_edu_input_file(dialogues, edu_input_file)
    dump_svmlight_file(X_gen, y_gen, out_file, comment=comment)

    # dump vocabulary
    vocab_file = out_file + '.vocab'
    dump_vocabulary(vzer.vocabulary_, vocab_file)



def main_corpus_pairs(args):
    """
    The usual main. Extract feature vectors from the corpus
    """
    inputs = features.read_corpus_inputs(args)
    dialogues = list(mk_high_level_dialogues(inputs, args.parsing))
    # these paths should go away once we switch to a proper dumper
    out_file = fp.join(args.output, fp.basename(args.corpus))
    out_file += '.relations.sparse'
    instance_generator = lambda x: x.edu_pairs(args.window)

    labels = frozenset(SUBORDINATING_RELATIONS +
                       COORDINATING_RELATIONS)

    # pylint: disable=invalid-name
    # scikit-convention
    feats = extract_pair_features(inputs, args.window, live=args.parsing)
    vzer = KeyGroupVectorizer()
    X_gen = vzer.fit_transform(feats)
    # pylint: enable=invalid-name
    labtor = LabelVectorizer(instance_generator, labels)
    y_gen = labtor.transform(dialogues)

    if not fp.exists(args.output):
        os.makedirs(args.output)

    dump_all(X_gen,
             y_gen,
             out_file,
             labtor.labelset_,
             dialogues,
             instance_generator)
    # dump vocabulary
    vocab_file = out_file + '.vocab'
    dump_vocabulary(vzer.vocabulary_, vocab_file)


def main(args):
    "main for feature extraction mode"

    if args.parsing and args.single:
        sys.exit("Can't mixing --parsing and --single")
    elif args.parsing:
        raise Exception('Still broken')
        #main_parsing_pairs(args)
    elif args.single:
        main_corpus_single(args)
    else:
        main_corpus_pairs(args)
