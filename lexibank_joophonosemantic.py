import pathlib

import attr
import pybtex.database
from pycldf.sources import Source
from pylexibank import Language, Dataset as BaseDataset
from pylexibank.util import progressbar
from clldutils.misc import slug


@attr.s
class CustomLanguage(Language):
    NameInSource = attr.ib(default=None)
    Source = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "joophonosemantic"
    language_class = CustomLanguage

    def cmd_makecldf(self, args):
        data = self.raw_dir.read_csv('raw.tsv', delimiter="\t", dicts=True)

        # Quite a hack to allow things like "1995.pdfb" as Source IDs:
        bib = pybtex.database.parse_string(self.raw_dir.read('sources.bib'), bib_format='bibtex')
        sources = []
        for k, e in bib.entries.items():
            # Unfortunately, Source.from_entry does not allow any keyword arguments to be passed
            # to the constructor, see https://github.com/cldf/pycldf/issues/99
            e.fields['_check_id'] = False
            sources.append(Source.from_entry(k, e))
        args.writer.add_sources(*sources)

        language_lookup = args.writer.add_languages(lookup_factory='NameInSource')
        concept_lookup = args.writer.add_concepts(
            id_factory=lambda x: x.id.split('-')[-1]+'_'+slug(x.english),
            lookup_factory='Name'
        )
        lang_sources = {l['NameInSource']: l['Source'].split(",") for l in self.languages}

        # remap concepts for personal pronouns
        remap_concepts = {
            '1SG pronoun': '1sg pronoun',
            '2SG pronoun': '2sg pronoun',
            '3SG pronoun': '3sg pronoun',
        }
        # remapping big vowel symbols to schwa
        remap_sounds = {
            '‼': '‼/ǃ',
            'V': 'V/ə',
            'tʃʔ': 'tʃˀ',
            'l̴': 'ł',
            'n!': 'ŋǃ',
            'ɡ|': 'g|',
            'ɡ‖': 'g‖',
        }

        for line_dict in progressbar(data, desc='cldfify'):
            concept = line_dict['Meaning']
            concept_id = concept_lookup.get(remap_concepts.get(concept, concept))
            for language, language_id in language_lookup.items():
                value = line_dict[language].strip()
                if value.strip():
                    tokens = [
                        remap_sounds.get(x, x) for x in value.strip('.').split('.') if x.strip()]
                    args.writer.add_form_with_segments(
                        Value=value,
                        Form=value,
                        Segments=tokens,
                        Parameter_ID=concept_id,
                        Language_ID=language_id,
                        Source=lang_sources[language]
                    )
