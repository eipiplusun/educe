"""
Educe representation of Penn Tree Bank annotations.

We actually just use the token and constituency tree representations
from `educe.external.postag` and `educe.external.parse`, but included
here are tools that can also be used to align the PTB with other
corpora based off the same text (eg. the RST Discourse Treebank)
"""

# Author: Eric Kow
# License: CeCILL-B (French BSD3-like)

import re

from educe.external.postag import RawToken


PTB_TO_TEXT = {"``": "\"",
               "''": "\"",
               "-LRB-": "(",
               "-RRB-": ")",
               "-LSB-": "[",
               "-RSB-": "]",
               "-LCB-": "{",
               "-RCB-": "}"}
"""
Straight substitutions you can use to replace some PTB-isms
with their likely original text
"""


# prefixes for things we can skip
_SKIP_RE = re.compile(r'^(' +
                      r'(\*((T|ICH|EXP|RNR|PPA)\*)?-\d*)' +
                      r'|0|\*' +
                      r'|(\*(U|\?|NOT)\*)' +
                      r')$')


def is_nonword_token(text):
    """
    True if the text appears to correspond to some kind of non-textual
    token, for example, `*T*-1` for some kind of trace. These seem to
    only appear with tokens tagged `-NONE-`.
    """
    return bool(_SKIP_RE.match(text))


#pylint: disable=too-few-public-methods
class TweakedToken(RawToken):
    """
    A token with word, part of speech, plus "tweaked word" (what the
    token should be treated as when aligning with corpus), and offset
    (some tokens should skip parts of the text)

    This intermediary class should only be used within the educe library
    itself. The context is that we sometimes want to align PTB
    annotations (see `educe.external.postag.generic_token_spans`)
    against text which is almost but not quite identical to
    the text that PTB annotations seem to represent. For example, the
    source text might have sentences that end in abbreviations, like
    "He moved to the U.S." and the PTB might annotation an extra full
    stop after this for an end-of-sentence marker. To deal with these,
    we use wrapped tokens to allow for some manual substitutions:

    * you could "delete" a token by assigning it an empty tweaked word
      (it would then be assigned a zero-length span)
    * you could skip some part of the text by supplying a prefix
      (this expands the tweaked word, and introduces an offset which
      you can subsequentnly use to adjust the detected token span)
    * or you could just replace the token text outright

    These tweaked tokens are only used to obtain a span within the text
    you are trying to align against; they can be subsequently discarded.
    """

    def __init__(self, word, tag, tweaked_word=None, prefix=None):
        tweak = word if tweaked_word is None else tweaked_word
        if prefix is None:
            offset = 0
        else:
            tweak = prefix + tweak
            offset = len(prefix)
        self.tweaked_word = tweak
        self.offset = offset
        super(TweakedToken, self).__init__(word, tag)

    def __str__(self):
        return unicode(self)

    def __unicode__(self):
        res = self.word
        if self.tweaked_word != self.word:
            res += " [%s]" % self.tweaked_word
        res += "/%s" % self.tag
        if self.offset != 0:
            res += " (%d)" % self.offset
        return res
#pylint: enable=too-few-public-methods


#
# TreebankLanguagePack (after edu.stanford.nlp.trees)
#
_gf_character = '-'  # (default) grammatical function character
# label annotation introducing characters
_laic = ['-',  # function tags, identity index, reference index
         '=',  # gap co-indexing
]


def post_basic_category_index(label):
    """Get the index of the first char after the basic label.

    This should never match the first char of the label ;
    if the first char is such a char, then a matched char is also
    not used iff there is something in between, e.g.
    (-LRB- => -LRB-) but (--PU => -).
    """
    first_char = ''
    for i, c in enumerate(label):
        if c in _laic:
            if i == 0:
                first_char = c
            elif first_char and (i > 1) and (c == first_char):
                first_char = ''
            else:
                break
    else:
        i += 1
    return i


def basic_category(label):
    """Get the basic syntactic category of a label.

    This is done by truncating whatever comes after a
    (non-word-initial) occurrence of one of the
    label_annotation_introducing_characters().
    """
    return label[0:post_basic_category_index(label)] if label else label


# Reimplementation of most of the most standard parser parameters for the PTB
# ref: edu.stanford.nlp.parser.lexparser.EnglishTreebankParserParams
def strip_subcategory(tree,
                      retain_TMP_subcategories=False,
                      retain_NPTMP_subcategories=False):
    """ """
    label = treenode(tree)
    if isinstance(tree, ConstituencyTree):
        if retain_TMP_subcategories and ('-TMP' in label):
            label = '{bc}-TMP'.format(bc=basic_category(label))
        elif retain_NPTMP_subcategories and label.startswith('NP-TMP'):
            label = 'NP-TMP'
        else:
            label = basic_category(label)
    # TODO: replace label in tree
    return tree
    
