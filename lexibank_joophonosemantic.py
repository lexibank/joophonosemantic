import attr
from pathlib import Path

from pylexibank import Concept, Language
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.util import pb

import lingpy
from clldutils.misc import slug

@attr.s
class CustomLanguage(Language):
    Latitude = attr.ib(default=None)
    Longitude = attr.ib(default=None)
    NameInSource = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "joophonosemantic"
    language_class=CustomLanguage

    def cmd_makecldf(self, args):
        data = self.raw_dir.read_csv('raw.tsv', delimiter="\t")
        args.writer.add_sources()
        header = data[0]
        if not self.languages:
            language_lookup = {}
            for cell in pb(header[1:], desc='search for glottocodes'):
                family, language = cell.split('/')
                language, iso = language.strip().split('[')
                iso = iso[:-1]
                language_id = slug(language, lowercase=False)
                glottolog = self.glottolog.glottocode_by_iso.get(iso, '')
                language_lookup[cell] = language_id
                args.writer.add_language(
                        Name=language.strip(),
                        ID=language_id,
                        ISO639P3code=iso,
                        Glottocode=glottolog,
                        Family=family.strip(),
                        Latitude=self.glottolog.languoid(glottolog).latitude,
                        Longitude=self.glottolog.languoid(glottolog).longitude,
                        NameInSource=cell
                        )
        else:
            language_lookup = args.writer.add_languages(lookup_factory='NameInSource')
        concept_lookup = concepts = args.writer.add_concepts(
                id_factory=lambda x: x.id.split('-')[-1]+'_'+slug(x.english),
                lookup_factory='Name'
                )
        # remap concepts for personal pronouns
        remap_concepts = {'1SG pronoun': '1sg pronoun', '2SG pronoun': '2sg pronoun',
                '3SG pronoun': '3sg pronoun'}
        # remapping big vowel symbols to schwa
        remap_sounds = {'‼': '‼/ǃ', 'V': 'V/ə', 'tʃʔ': 'tʃˀ', 'l̴': 'ł', 
                'n!': 'ŋǃ', 'ɡ|': 'g|', 'ɡ‖': 'g‖'}

        for line in pb(data[1:], desc='cldfify'):
            concept, concept_id = line[0], concept_lookup.get(
                    remap_concepts.get(line[0], line[0]))
            line_dict = dict(zip(header, line))
            for language, language_id in language_lookup.items():
                value = line_dict[language]
                if value.strip():
                    tokens = [remap_sounds.get(x, x) for x in value.strip('.').split('.') if
                        x.strip()]
                    args.writer.add_form_with_segments(
                            Value=value,
                            Form=value,
                            Segments=tokens,
                            Parameter_ID=concept_id,
                            Language_ID=language_id,
                            Source=[]
                            )

