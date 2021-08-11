import nltk

nltk.download('wordnet')
from nltk.corpus import wordnet
from django.conf import settings

dict_wn = nltk.corpus.wordnet
words = [w for w in list(set(w for w in dict_wn.words())) if ('_' not in w)]


def preload_data():
    """
        This will pre load all synonyms and lemmas.
    """
    get_synonyms()
    get_lemmas()


def get_synonyms():
    if settings.SYNONYMS:
        return
    all_synonyms = {'nouns': {}, 'verbs': {}, 'adjectives': {}, 'adverbs': {}}
    pos_map = {'nouns': ['n'], 'adjectives': ['a', 's'], 'verbs': ['v'], 'adverbs': ['r']}
    for idx, word in enumerate(words):
        for pos in pos_map.keys():
            synonyms = []
            definition = ""
            for synset in dict_wn.synsets(word, pos=pos_map[pos]):
                synonyms.extend([syn.lower()
                                 for syn in synset.lemma_names() if "_" not in syn])
                if not definition:
                    pass
            synonyms = list(set(synonyms) - set(word))
            if synonyms:
                all_synonyms[pos][word] = synonyms
    settings.SYNONYMS = all_synonyms


def get_lemmas():
    print('starting...')
    print('loaded WordNet data.')

    print('starting to look for base lemmas...')
    base_lemmas = {}
    for idx, word in enumerate(words):
        if word not in base_lemmas.keys():
            related_lemmas = []
            stack = [lemma for lemma in dict_wn.lemmas(word)]
            while stack:
                related_lemmas.extend(stack)
                stack = [lm for lemma in stack for lm in lemma.derivationally_related_forms() if
                         (lm not in related_lemmas)]
            related_words = list(set([lm.name().lower() for lm in related_lemmas]))
            related_words_len = [len(w) for w in related_words]
            base_lemma = related_words[related_words_len.index(min(related_words_len))]
            base_lemmas.update({word: base_lemma for word in related_words if (word != base_lemma)})
    print('created dictionary of base lemmas.')
    print(' ')
    print(len(base_lemmas))

    settings.LEMMAS = base_lemmas
