def find_sentence_and_types(data, doc, metrics):
    sents = []
    sents_end_punct = []
    sents_start_idx = []
    new_sent = []
    print("SENTENCE ANALYSIS")
    for sent in doc.sents:
        if not new_sent:
            sents_start_idx.append(sent.start)
        new_sent.extend(sent)
        for token in reversed(sent):
            if token.text[0] in ['.', '?', '!']:
                sents.append(new_sent)
                sents_end_punct.append(token.text[0])
                new_sent = []
                break
    if new_sent:
        sents.append(new_sent)
        sents_end_punct.append(None)
    data['sentence_numbers'] = [(idx + 1) for idx, sent in enumerate(sents) for token in sent]
    data['sentence_end_punctuations'] = [sents_end_punct[idx] for idx, sent in enumerate(sents) for token in sent]

    # find subjects, predicates, clauses and sentence types based on syntactic structure
    data['principal_parts'] = [None] * len(doc)
    data['independent_principal_parts'] = [None] * len(doc)
    sents_types = ['simple'] * len(sents)
    sents_clauses = [0] * len(sents)
    subj_tags = ['nsubj', 'nsubjpass', 'expl']
    for idx, sent in enumerate(sents):
        is_compound = False
        is_complex = False
        roots = [token for token in  sent if (token.dep_ == 'ROOT') and (token.pos_ == 'VERB')]
        if not roots:
            sents_types[idx] = 'fragment'
            sents_clauses[idx] = 1
            continue
        for root in roots:
            data['independent_principal_parts'][root.i] = 'predicate'
            data['principal_parts'][root.i] = 'predicate'
            sents_clauses[idx] += 1
        for subj in [token for token in sent if (token.dep_ in subj_tags) and (token.head.pos_ == 'VERB')]:
            data['principal_parts'][subj.i] = 'subject'
            if subj.head.dep_ == 'ROOT':
                data['independent_principal_parts'][subj.i] = 'subject'
            else:
                data['principal_parts'][subj.head.i] = 'predicate'
                sents_clauses[idx] += 1
                if subj.head.dep_ in ['parataxis', 'conj']:
                    is_compound = True
                else:
                    is_complex = True
        for conj in [token for token in sent if (token.dep_ == 'conj') and not data['principal_parts'][token.i]]:
            data['principal_parts'][conj.i] = data['principal_parts'][conj.head.i]
            data['independent_principal_parts'][conj.i] = data['independent_principal_parts'][conj.head.i]
        if is_complex and is_compound:
            sents_types[idx] = 'complex-compound'
        elif is_compound:
            sents_types[idx] = 'compound'
        elif is_complex:
            sents_types[idx] = 'complex'
    data['sentence_types'] = [sents_types[idx] for idx, sent in enumerate(sents) for token in sent]
    return data, metrics, sents, sents_types, sents_end_punct, sents_clauses, sents_start_idx


def compute_sentence_metrics(metrics, doc, sents_types, sents_end_punct):
    if metrics['sentence_count']:
        metrics['declarative_ratio'] = sents_end_punct.count('.') / metrics['sentence_count']
        metrics['interrogative_ratio'] = sents_end_punct.count('?') / metrics['sentence_count']
        metrics['exclamative_ratio'] = sents_end_punct.count('!') / metrics['sentence_count']
    else:
        metrics['declarative_ratio'] = 0
        metrics['interrogative_ratio'] = 0
        metrics['exclamative_ratio'] = 0

        # count sentence types based on clause structure
    if metrics['sentence_count']:
        metrics['simple_ratio'] = sents_types.count('simple') / metrics['sentence_count']
        metrics['fragment_ratio'] = sents_types.count('fragment') / metrics['sentence_count']
        metrics['complex_ratio'] = sents_types.count('complex') / metrics['sentence_count']
        metrics['compound_ratio'] = sents_types.count('compound') / metrics['sentence_count']
        metrics['complex_compound_ratio'] = sents_types.count('complex-compound') / metrics['sentence_count']
    else:
        metrics['simple_ratio'] = 0
        metrics['fragment_ratio'] = 0
        metrics['complex_ratio'] = 0
        metrics['compound_ratio'] = 0
        metrics['complex_compound_ratio'] = 0

    return metrics
