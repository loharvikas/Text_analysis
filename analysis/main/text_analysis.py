import spacy
import nltk
from django.conf import settings
from numpy import std
from .sentence_analysis import find_sentence_and_types, compute_sentence_metrics
import re

nltk.download('wordnet')
dict_wn = nltk.corpus.wordnet
nlp = spacy.load('en_core_web_sm')
quotation_re = re.compile(u'[\u00AB\u00BB\u201C\u201D\u201E\u201F\u2033\u2036\u301D\u301E]')
apostrophe_re = re.compile(u'[\u02BC\u2019\u2032]')


def parse_text(data, doc):
    print("PARSING")
    data['values'] = [token.text for token in doc]
    data['parts_of_speech'] = [token.tag_ for token in doc]
    data['pos_high_level'] = [token.pos_ for token in doc]
    data['syntax_relations'] = [token.dep_ for token in doc]
    data['words'] = [is_word(token) for token in doc]
    data['punctuation_marks'] = [token.is_punct for token in doc]
    data['numbers_of_characters'] = [len(token.text) if is_word(token) else None for token in doc]
    data["stopwords"] = [token.is_stop for token in doc]
    return data


def is_word(token):
    return token.text[0].isalnum() or (
            token.pos_ in ['VERB', 'PRON'])


def find_synonyms(data, doc, words, word2token_map):
    """
        Uses pre load synonyms and lemmas loaded in load_data.py
    """
    data['lemmas'] = [token.lemma_ if is_word(token) else None for token in doc]
    dict_synonyms = settings.SYNONYMS
    dict_base_lemmas = settings.LEMMAS
    data['synonyms'] = [None] * len(doc)
    data['base_lemmas'] = [None] * len(doc)

    for idx, lemma in enumerate(data['lemmas']):
        if lemma == '-PRON-':  # spaCy replaces pronouns with '-PRON-' so we need to fix it
            data['lemmas'][idx] = data['values'][idx].lower()

    pos_map = {'NN': 'nouns', 'JJ': 'adjectives', 'VB': 'verbs', 'RB': 'adverbs'}
    for idx_word, word in enumerate(words):
        idx = word2token_map[idx_word]
        pos = data['parts_of_speech'][idx][:2]
        if (pos in pos_map) and (word in dict_synonyms[pos_map[pos]]):
            data['synonyms'][idx] = dict_synonyms[pos_map[pos]][word]
        else:
            data['synonyms'][idx] = []
        if data['lemmas'][idx] in dict_base_lemmas:
            data['base_lemmas'][idx] = dict_base_lemmas[data['lemmas'][idx]]
        else:
            data['base_lemmas'][idx] = data['lemmas'][idx]
    return data


def verb_analysis(data, doc):
    print("VERB ANALYSIS")
    data['verb_groups'] = [None] * len(doc)
    data['auxiliary_verbs'] = [False if is_word(token) else None for token in doc]
    verb_group_stack = []
    verb_group_count = 0
    for idx, token in enumerate(doc):
        if not verb_group_stack:
            if token.text in ["be", "am", "'m", "is", "are", "'re", "was", "were", "will", "'ll", "wo", "have", "'ve",
                              "has", "had", "'d"]:
                verb_group_stack.append(idx)
            elif (token.text == "'s") and (token.pos_ == 'VERB'):
                verb_group_stack.append(idx)
        elif token.text in ['be', 'been', 'being', 'have', 'had']:
            verb_group_stack.append(idx)
        elif data['pos_high_level'][idx] == 'VERB':
            verb_group_stack.append(idx)
            verb_group_count += 1
            for i in verb_group_stack:
                data['verb_groups'][i] = verb_group_count
            for j in verb_group_stack[:-1]:
                data['auxiliary_verbs'][j] = True
            verb_group_stack = []
        elif data['parts_of_speech'][idx][:2] not in ['RB', 'PD']:
            if len(verb_group_stack) > 1:
                verb_group_count += 1
                for i in verb_group_stack:
                    data['verb_groups'][i] = verb_group_count
                for j in verb_group_stack[:-1]:
                    data['auxiliary_verbs'][j] = True
            verb_group_stack = []
    return data


def analyze_text(text):
    text = quotation_re.sub('"', text)
    text = apostrophe_re.sub("'", text)
    data = {}
    metrics = {}
    doc = nlp(text)
    data = parse_text(data, doc)
    words = []
    word2token_map = []
    for idx, token in enumerate(doc):
        if data['words'][idx]:
            words.append(token.lower_)
            word2token_map.append(idx)
    data = find_synonyms(data, doc, words, word2token_map)
    data = verb_analysis(data, doc)
    words = []
    word2token_map = []
    for idx, token in enumerate(doc):
        if data['words'][idx]:
            words.append(token.lower_)
            word2token_map.append(idx)

    data, metrics, sents, sents_types, sents_end_punct, sents_clauses, sents_start_idx = find_sentence_and_types(data,
                                                                                                                 doc,
                                                                                                                 metrics)
    sents_words = [[token.lower_ for token in sent if is_word(token)] for sent in sents]
    sents_length = [len(sent) for sent in sents_words]
    metrics["sentence_count"] = len(sents)
    metrics['word_count'] = len(words)
    print("BASE:", len(set(data['base_lemmas'])))
    metrics['vocabulary_size'] = len(set(data['base_lemmas'])) - 1
    if len(sents_length):
        metrics['words_per_sentence'] = sum(sents_length) / len(sents_length)
    else:
        metrics['words    _per_sentence'] = 0
    if len(sents_length) >= 10:
        metrics['std_of_words_per_sentence'] = std(sents_length)
    else:
        metrics['std_of_words_per_sentence'] = -1
    if len(sents_length):
        metrics['long_sentences_ratio'] = len([1 for sent_length in sents_length if sent_length >= 40]) / len(
            sents_length)
        metrics['short_sentences_ratio'] = len([1 for sent_length in sents_length if sent_length <= 6]) / len(
            sents_length)
    else:
        metrics['long_sentences_ratio'] = 0
        metrics['short_sentences_ratio'] = 0
    metrics = compute_sentence_metrics(metrics, doc, sents_types, sents_end_punct)
    metrics, data = compute_clause_metrics(doc, metrics, data, sents, sents_start_idx, sents_clauses)
    metrics, data = compute_text_metrics(doc, metrics, data, text, words)
    metrics = compute_pos_metrics(data, metrics)
    return data, metrics


def compute_pos_metrics(data, metrics):
    noun_count = 0
    pronoun_count = 0
    pronoun_nonpossesive_count = 0
    verb_count = 0
    adjective_count = 0
    adverb_count = 0
    for tag in data['parts_of_speech']:
        if tag[:2] == 'NN':
            noun_count += 1
        elif tag[:2] in ['PR', 'WP', 'EX']:
            pronoun_count += 1
            if tag in ['PRP', 'WP', 'EX']:
                pronoun_nonpossesive_count += 1
        elif tag[:2] in ['VB', 'MD']:
            verb_count += 1
        elif tag[:2] == 'JJ':
            adjective_count += 1
        elif tag[:2] == 'RB':
            adverb_count += 1
    if metrics['word_count']:
        metrics['noun_ratio'] = noun_count / metrics['word_count']
        metrics['pronoun_ratio'] = pronoun_count / metrics['word_count']
        metrics['verb_ratio'] = verb_count / metrics['word_count']
        metrics['adjective_ratio'] = adjective_count / metrics['word_count']
        metrics['adverb_ratio'] = adverb_count / metrics['word_count']
        metrics['other_pos_ratio'] = 1 - metrics['noun_ratio'] - metrics['pronoun_ratio'] - metrics['verb_ratio'] \
                                     - metrics['adjective_ratio'] - metrics['adverb_ratio']
    else:
        metrics['noun_ratio'] = 0
        metrics['pronoun_ratio'] = 0
        metrics['verb_ratio'] = 0
        metrics['adjective_ratio'] = 0
        metrics['adverb_ratio'] = 0
        metrics['other_pos_ratio'] = 0

    # count number of modals
    modal_count = data['parts_of_speech'].count('MD')
    if metrics['word_count']:
        metrics['modal_ratio'] = modal_count / metrics['word_count']
    else:
        metrics['modal_ratio'] = 0
    return metrics


def compute_text_metrics(doc, metrics, data, text, words):
    # count number of characters in the whole text
    metrics['character_count'] = len(text)

    # count number of characters per word
    char_count = [len(word) for word in words]
    if metrics['word_count']:
        metrics['characters_per_word'] = sum(char_count) / metrics['word_count']
    else:
        metrics['characters_per_word'] = 0

    # count stopwords
    if metrics['word_count']:
        metrics['stopword_ratio'] = data['stopwords'].count(True) / metrics['word_count']
    else:
        metrics['stopword_ratio'] = 0

    return metrics, data


def compute_clause_metrics(doc, metrics, data, sents, sents_start_idx, sents_clauses):
    # compute subject-, predicate- and clause-related metrics
    data['clause_heavy_sentences'] = [False] * len(doc)
    sents_predicate_depth = [0] * len(sents)
    data['late_predicates'] = [False] * len(doc)
    data['detached_subjects'] = [False] * len(doc)
    metrics['many_clauses_ratio'] = 0
    metrics['late_predicates_ratio'] = 0
    metrics['detached_subjects_ratio'] = 0
    sents_with_predicate_count = 0
    for idx, sent in enumerate(sents):
        s1 = sents_start_idx[idx]
        s2 = sents_start_idx[idx] + len(sent)
        syntax_mask = data['independent_principal_parts'][s1:s2]
        if 'predicate' in syntax_mask:
            pred_idx = syntax_mask.index('predicate')
            pred_depth = sum([1 for token in sent[:pred_idx] if is_word(token)]) + 1
            sents_with_predicate_count += 1
        else:
            continue
        sents_predicate_depth[idx] = pred_depth
        if sents_clauses[idx] >= 4:
            data['clause_heavy_sentences'][s1:s2] = [(i is not None) for i in data['principal_parts'][s1:s2]]
            metrics['many_clauses_ratio'] += 1
        if pred_depth > 15:
            data['late_predicates'][sents_start_idx[idx] + pred_idx] = True
            metrics['late_predicates_ratio'] += 1
        if 'subject' in syntax_mask:
            subj_idx = syntax_mask.index('subject')
            subj_depth = sum([1 for token in sent[:subj_idx] if is_word(token)])
            if pred_depth - subj_depth > 8:
                data['detached_subjects'][sents_start_idx[idx] + pred_idx] = True
                data['detached_subjects'][sents_start_idx[idx] + subj_idx] = True
                metrics['detached_subjects_ratio'] += 1
    if sents_with_predicate_count:
        metrics['predicate_depth'] = sum(sents_predicate_depth) / sents_with_predicate_count
        metrics['late_predicates_ratio'] = metrics['late_predicates_ratio'] / sents_with_predicate_count
        metrics['detached_subjects_ratio'] = metrics['detached_subjects_ratio'] / sents_with_predicate_count
    else:
        metrics['predicate_depth'] = 0
    if metrics['sentence_count']:
        metrics['clauses_per_sentence'] = sum(sents_clauses) / metrics['sentence_count']
        metrics['many_clauses_ratio'] = metrics['many_clauses_ratio'] / metrics['sentence_count']
    else:
        metrics['clauses_per_sentence'] = 0
        metrics['many_clauses_ratio'] = 0

    return metrics, data
