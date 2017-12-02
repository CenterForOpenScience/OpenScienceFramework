import os
import re

from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON

from osf.models import PreprintService
from website.citations.utils import datetime_to_csl
from website.settings import CITATION_STYLES_PATH, BASE_PATH, CUSTOM_CITATIONS
from framework.auth import utils


def clean_up_common_errors(cit):
    cit = re.sub(r"\.+", '.', cit)
    cit = re.sub(r" +", ' ', cit)
    return cit


def display_absolute_url(node):
    url = node.absolute_url
    if url is not None:
        return re.sub(r'https?:', '', url).strip('/')


def preprint_csl(preprint, node):
    csl = node.csl

    csl['id'] = preprint._id
    csl['publisher'] = preprint.provider.name
    csl['URL'] = display_absolute_url(preprint)

    if preprint.original_publication_date:
        csl['issued'] = datetime_to_csl(preprint.original_publication_date)

    if csl.get('DOI'):
        csl.pop('DOI')

    doi = preprint.article_doi
    if doi:
        csl['DOI'] = doi

    return csl


def process_name(node, user):
    if user.is_registered or user.is_disabled:
        name = user.fullname
    else:
        name = user.get_unclaimed_record(node._id)['name']

    if user.family_name and user.given_name:
        """If the user has a family and given name, use those"""
        return {
            'family_name': user.family_name,
            'suffix': user.suffix,
            'given_name': user.given_name,
            'middle_names': user.middle_names,
        }
    else:
        """ If the user doesn't autofill his family and given name """
        parsed = utils.impute_names(name)
        given_name = parsed['given']
        middle_names = parsed['middle']
        family_name = parsed['family']
        suffix = parsed['suffix']
        return {
            'family_name': family_name,
            'suffix': suffix,
            'given_name': given_name,
            'middle_names': middle_names
        }


def render_citation(node, style='apa'):
    """Given a node, return a citation"""
    csl = None
    if isinstance(node, PreprintService):
        csl = preprint_csl(node, node.node)
        data = [csl, ]
    else:
        data = [node.csl, ]

    bib_source = CiteProcJSON(data)

    custom = CUSTOM_CITATIONS.get(style, False)
    path = os.path.join(BASE_PATH, 'static', custom) if custom else os.path.join(CITATION_STYLES_PATH, style)
    bib_style = CitationStylesStyle(path, validate=False)

    bibliography = CitationStylesBibliography(bib_style, bib_source, formatter.plain)

    citation = Citation([CitationItem(node._id)])

    bibliography.register(citation)

    bib = bibliography.bibliography()
    cit = unicode(bib[0] if len(bib) else '')

    title = csl['title'] if csl else node.csl['title']
    if cit.count(title) == 1:
        i = cit.index(title)
        prefix = clean_up_common_errors(cit[0:i])
        suffix = clean_up_common_errors(cit[i + len(title):])
        cit = prefix + title + suffix
    elif cit.count(title) == 0:
        cit = clean_up_common_errors(cit)

    if style == 'apa':
        if isinstance(node, PreprintService):
            cit = apa_reformat(node.node, cit)
        else:
            cit = apa_reformat(node, cit)
    if style == 'chicago-author-date':
        if isinstance(node, PreprintService):
            cit = chicago_reformat(node.node, cit)
        else:
            cit = chicago_reformat(node, cit)
    if style == 'modern-language-association':
        if isinstance(node, PreprintService):
            cit = mla_reformat(node.node, cit)
        else:
            cit = mla_reformat(node, cit)

    return cit


def apa_reformat(node, cit):
    new_csl = cit.split('(')
    contributors_list = [x for x in node.contributors if node.get_visible(x)]

    # handle only one contributor
    if len(contributors_list) == 1:
        name = process_name(node, contributors_list[0])
        new_apa = apa_name(name)
    # handle more than one contributor  but less than 8 contributors
    elif len(contributors_list) in range(1, 8):
        name_list = [apa_name(process_name(node, x)) for x in contributors_list[:-1]]
        new_apa = ' '.join(name_list)
        last_one = apa_name(process_name(node, contributors_list[-1]))
        new_apa += ' & ' + last_one
    # handle 8 or more contributors
    else:
        name_list = [apa_name(process_name(node, x)) for x in contributors_list[:6]]
        new_apa = ' '.join(name_list) + '... ' + apa_name(process_name(node, contributors_list[6]))

    cit = new_apa.rstrip(', ') + ' '
    for x in new_csl[1:]:
        cit += '(' + x
    return cit


def apa_name(name):
    apa = ''
    if name['family_name']:
        apa += name['family_name'] + ','
    if name['given_name']:
        apa += ' ' + name['given_name'][0] + '.'
        if name['middle_names']:
            apa += ' ' + name['middle_names'][0] + '.'
        apa += ','
    if name['suffix']:
        apa += ' ' + name['suffix'] + ','
    return apa


def mla_reformat(node, cit):
    contributors_list = [x for x in node.contributors if node.get_visible(x)]

    # handle only one contributor
    if len(contributors_list) == 1:
        name = process_name(node, contributors_list[0])
        new_mla = mla_name(name, initial=True).rstrip(' ')
    # handle more than one contributor  but less than 5 contributors
    elif len(contributors_list) in range(1, 5):
        first_one = mla_name(process_name(node, contributors_list[0]), initial=True)
        rest_ones = [mla_name(process_name(node, x)) for x in contributors_list[1:-1]]
        last_one = mla_name(process_name(node, contributors_list[-1]))
        if rest_ones:
            rest_part = ', '.join(rest_ones)
            new_mla = first_one + ', ' + rest_part + ', and ' + last_one
        else:
            new_mla = first_one + 'and ' + last_one
    # handle 5 or more contributors
    else:
        name = process_name(node, contributors_list[0])
        new_mla = mla_name(name, initial=True) + ' et al. '
    cit = new_mla
    cit += u' \u201c' + node.title.title() + u'.\u201d Open' + cit.split('Open')[-1]
    return cit


def chicago_reformat(node, cit):
    new_csl = cit.split('20')
    contributors_list = [x for x in node.contributors if node.get_visible(x)]

    # handle only one contributor
    if len(contributors_list) == 1:
        name = process_name(node, contributors_list[0])
        new_chi = mla_name(name, initial=True) + ' '
    # handle more than one contributor  but less than 8 contributors
    elif len(contributors_list) in range(1, 8):
        first_one = mla_name(process_name(node, contributors_list[0]), initial=True)
        rest_ones = [mla_name(process_name(node, x)) for x in contributors_list[1:-1]]
        last_one = mla_name(process_name(node, contributors_list[-1]))
        if rest_ones:
            rest_part = ', '.join(rest_ones)
            new_chi = first_one + ', ' + rest_part + ', and ' + last_one + ' '
        else:
            new_chi = first_one + 'and ' + last_one + ' '
    # handle 8 or more contributors
    else:
        new_chi = mla_name(process_name(node, contributors_list[0]), initial=True)
        name_list = [mla_name(process_name(node, x)) for x in contributors_list[1:7]]
        rest = ', '.join(name_list) + ' et al. '
        new_chi += ', ' + rest

    cit = new_chi
    for x in new_csl[1:]:
        cit += '20' + x
    return cit


def mla_name(name, initial=False):
    if initial:
        mla = ''
        if name['family_name']:
            mla += name['family_name'] + ','
        if name['given_name']:
            mla += ' ' + name['given_name']
            if name['middle_names']:
                mla += ' ' + name['middle_names'][0] + '.'
            mla += ','
        if name['suffix']:
            mla += ' ' + name['suffix']
    else:
        mla = ''
        if name['given_name']:
            mla += name['given_name']
            if name['middle_names']:
                mla += ' ' + name['middle_names'][0]
            mla += ','
        if name['suffix']:
            mla += ' ' + name['suffix']
        if name['family_name']:
            mla += ' ' + name['family_name']
    return mla
