"""
question_generator.py — Question Predictor 2.0 Engine for CareerMate AI.
Features:
  - extract_key_concepts: Extracts top document concepts & topics via POS tagging and frequency ranking.
  - group_questions_by_concept: Groups questions under relevant concept headings.
  - QuestionGenerator: Multi-format (Long, Short, MCQ) and multi-difficulty (Easy, Medium, Hard) generator.
"""

import re
import random
from collections import Counter
from typing import List, Dict, Any, Optional

try:
    import nltk
    for pkg in ['punkt', 'punkt_tab', 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng', 'stopwords']:
        try:
            nltk.data.find(f'tokenizers/{pkg}' if 'punkt' in pkg else (f'corpora/{pkg}' if 'stopwords' in pkg else f'taggers/{pkg}'))
        except Exception:
            nltk.download(pkg, quiet=True)
except Exception:
    pass


def extract_key_concepts(text: str, top_n: int = 10) -> List[str]:
    """
    Identifies the document's main topics/concepts using NLTK POS tagging
    and frequency ranking of noun phrases and technical keywords.
    """
    if not text:
        return ["General Technical Skills", "Project Architecture", "Problem Solving"]

    grammar = r"""
        CONCEPT: {<NNP>+<NNP|NN>*}
                 {<NN|NNS>+<NN|NNS>+}
                 {<JJ|JJR|JJS>*<NNP|NN>+}
    """
    
    stop_words = {
        "experience", "work", "project", "projects", "team", "year", "years",
        "candidate", "role", "time", "day", "management", "details", "page",
        "description", "responsibilities", "requirements", "skills", "university"
    }

    try:
        sentences = nltk.sent_tokenize(text)
        cp = nltk.RegexpParser(grammar)
        noun_phrases = []

        for s in sentences:
            tokens = nltk.word_tokenize(s)
            tagged = nltk.pos_tag(tokens)
            tree = cp.parse(tagged)
            for subtree in tree.subtrees():
                if subtree.label() == "CONCEPT":
                    phrase = " ".join(leaf[0] for leaf in subtree).strip()
                    phrase_clean = re.sub(r'^[^\w]+|[^\w]+$', '', phrase)
                    if len(phrase_clean) >= 3 and phrase_clean.lower() not in stop_words and len(phrase_clean.split()) <= 3:
                        noun_phrases.append(phrase_clean.title())

        if noun_phrases:
            counts = Counter(noun_phrases)
            top_concepts = [phrase for phrase, count in counts.most_common(top_n)]
            if top_concepts:
                return top_concepts
    except Exception:
        pass

    # Fallback with capitalized technical phrases
    candidates = re.findall(r'\b[A-Z][a-zA-Z0-9+#.-]*(?:\s+[A-Z][a-zA-Z0-9+#.-]*)*\b', text)
    filtered = [c.title() for c in candidates if len(c) >= 3 and c.lower() not in stop_words]
    counts = Counter(filtered)
    concepts = [c for c, _ in counts.most_common(top_n)]
    return concepts if concepts else ["Core Technology", "Software Design", "Application Development"]


def group_questions_by_concept(questions: List[Any], concepts: List[str]) -> Dict[str, List[Any]]:
    """
    Groups a list of generated questions under extracted key concepts using best-effort string matching.
    """
    grouped = {concept: [] for concept in concepts}
    unassigned_key = "General & Core Competencies"
    grouped[unassigned_key] = []

    for q in questions:
        # Determine question text to match
        if isinstance(q, dict):
            q_text = q.get("question", "") + " " + q.get("correct_answer", "") + " " + q.get("explanation", "")
        else:
            q_text = str(q)

        matched_concept = None
        for concept in concepts:
            # Check full concept or word parts
            if re.search(r'\b' + re.escape(concept.lower()) + r'\b', q_text.lower()):
                matched_concept = concept
                break
            # Check individual tokens of multi-word concepts
            concept_words = [w for w in concept.lower().split() if len(w) > 3]
            if any(re.search(r'\b' + re.escape(w) + r'\b', q_text.lower()) for w in concept_words):
                matched_concept = concept
                break

        if matched_concept:
            grouped[matched_concept].append(q)
        else:
            grouped[unassigned_key].append(q)

    # Filter out empty concept groups
    filtered_grouped = {k: v for k, v in grouped.items() if len(v) > 0}
    if not filtered_grouped:
        filtered_grouped[unassigned_key] = questions

    return filtered_grouped


class QuestionGenerator:
    """
    Generates tailored interview questions across multiple formats (Long, Short, MCQ),
    difficulty levels, and concept groupings.
    """

    GRAMMAR = r"""
        CHUNK: {<NN|NNP>+<IN|DT>*<NN|NNP|NNS>+}
        {<NNP>+<NNS>*}
        {<JJ|JJR|JJS>*<NN|NNP|NNS>+}
    """

    LONG_PATTERNS = {
        "easy": [
            "Explain what you accomplished with ",
            "Describe the basic purpose and usage of ",
            "Explain in simple terms what is ",
            "What was your primary responsibility regarding "
        ],
        "medium": [
            "Explain in detail how you designed and implemented ",
            "How did you leverage {} to solve key project challenges?",
            "Elaborate on the workflow and architecture when working with ",
            "Explain with a concrete example how you utilized ",
            "Discuss the integration process and advantages of "
        ],
        "hard": [
            "Deep-dive into the architectural trade-offs and performance bottlenecks of ",
            "How would you scale, optimize, and handle failure modes for ",
            "Critically analyze the security, concurrency, and reliability aspects of ",
            "Explain how you debugged complex production issues involving "
        ]
    }

    SHORT_PATTERNS = {
        "easy": [
            "What is ",
            "Define ",
            "What does {} stand for or represent?",
            "Name the primary purpose of "
        ],
        "medium": [
            "Briefly describe the role of ",
            "What are the core advantages of using ",
            "Which key features distinguish ",
            "In one or two sentences, explain "
        ],
        "hard": [
            "What is the underlying mechanism behind ",
            "State the main distinction between {} and alternative approaches.",
            "What is the time/space complexity or performance implication of "
        ]
    }

    def __init__(self, data: str, no_of_questions: int = 10, difficulty: str = "medium"):
        self.summary = data or ""
        self.no_of_questions = int(no_of_questions) if no_of_questions else 10
        self.difficulty = difficulty.lower() if difficulty in ("easy", "medium", "hard") else "medium"
        self.concepts = extract_key_concepts(self.summary, top_n=8)

    def _get_sentences(self) -> List[str]:
        """Split summary into sentences, filtered by difficulty heuristics."""
        try:
            sentences = nltk.sent_tokenize(self.summary)
        except Exception:
            sentences = [s.strip() for s in re.split(r'[.\n!?;]+', self.summary) if len(s.strip()) > 15]

        filtered = []
        for s in sentences:
            s_clean = s.strip()
            word_count = len(s_clean.split())
            if word_count < 4:
                continue

            if self.difficulty == "easy" and word_count <= 22:
                filtered.append(s_clean)
            elif self.difficulty == "medium" and 10 <= word_count <= 35:
                filtered.append(s_clean)
            elif self.difficulty == "hard" and word_count >= 18:
                filtered.append(s_clean)
            else:
                filtered.append(s_clean)

        return filtered if filtered else sentences

    def _extract_chunks_with_context(self) -> List[Dict[str, Any]]:
        """Extract noun-phrase chunks paired with their source sentence context."""
        sentences = self._get_sentences()
        chunks = []

        try:
            cp = nltk.RegexpParser(self.GRAMMAR)
        except Exception:
            cp = None

        for sent in sentences:
            try:
                tokens = nltk.word_tokenize(sent)
                tagged = nltk.pos_tag(tokens)
                if cp:
                    tree = cp.parse(tagged)
                    for subtree in tree.subtrees():
                        if subtree.label() == "CHUNK":
                            chunk_text = " ".join(leaf[0] for leaf in subtree).strip()
                            chunk_text = re.sub(r'^[^\w]+|[^\w]+$', '', chunk_text)
                            if len(chunk_text) >= 3 and len(chunk_text.split()) <= 4 and not chunk_text.lower().startswith(("http", "www")):
                                chunks.append({
                                    "chunk": chunk_text,
                                    "sentence": sent,
                                    "word_count": len(tokens)
                                })
            except Exception:
                words = re.findall(r'\b[A-Z][a-zA-Z0-9+#.-]*(?:\s+[A-Z][a-zA-Z0-9+#.-]*)*\b', sent)
                for w in words:
                    if len(w) >= 3:
                        chunks.append({
                            "chunk": w,
                            "sentence": sent,
                            "word_count": len(sent.split())
                        })

        return chunks

    def generate_long_answer_questions(self, n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Generate in-depth subjective/behavioral interview questions.
        Returns list of structured question dicts with type & difficulty tags.
        """
        limit = n if n is not None else self.no_of_questions
        chunks_data = self._extract_chunks_with_context()
        patterns = self.LONG_PATTERNS.get(self.difficulty, self.LONG_PATTERNS["medium"])

        questions = []
        seen = set()

        for item in chunks_data:
            chunk = item["chunk"]
            chunk_upper = chunk.strip().title()
            if chunk_upper.lower() in seen or len(chunk_upper) < 3:
                continue

            seen.add(chunk_upper.lower())
            pat = random.choice(patterns)
            if "{}" in pat:
                q = pat.format(chunk_upper)
            else:
                q = f"{pat}{chunk_upper}?"

            if not q.endswith("?"):
                q += "?"

            questions.append({
                "question": q,
                "type": "Long Answer",
                "difficulty": self.difficulty.capitalize(),
                "topic": chunk_upper
            })

            if len(questions) >= limit:
                break

        # Fallbacks
        if len(questions) < limit:
            fallbacks = [
                "Describe your key technical strengths and contributions in your latest project.",
                "How do you approach debugging and problem solving in production environments?",
                "Explain the end-to-end architecture of a major application you developed.",
                "How do you ensure test coverage, code quality, and maintainability in your team?",
                "Discuss a challenging technical problem you solved and the trade-offs involved."
            ]
            for fb in fallbacks:
                if not any(q["question"] == fb for q in questions):
                    questions.append({
                        "question": fb,
                        "type": "Long Answer",
                        "difficulty": self.difficulty.capitalize(),
                        "topic": "General Architecture"
                    })
                if len(questions) >= limit:
                    break

        return questions[:limit]

    # Alias for legacy compatibility (returns strings if called directly)
    def generate_questions(self):
        long_q = self.generate_long_answer_questions()
        return [q["question"] for q in long_q]

    def generate_short_answer_questions(self, n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Generate concise, targeted conceptual questions.
        """
        limit = n if n is not None else self.no_of_questions
        chunks_data = self._extract_chunks_with_context()
        patterns = self.SHORT_PATTERNS.get(self.difficulty, self.SHORT_PATTERNS["medium"])

        questions = []
        seen = set()

        for item in chunks_data:
            chunk = item["chunk"].strip().title()
            if chunk.lower() in seen or len(chunk) < 3:
                continue

            seen.add(chunk.lower())
            pat = random.choice(patterns)
            if "{}" in pat:
                q = pat.format(chunk)
            else:
                q = f"{pat}{chunk}?"

            if not q.endswith("?"):
                q += "?"

            questions.append({
                "question": q,
                "type": "Short Answer",
                "difficulty": self.difficulty.capitalize(),
                "topic": chunk
            })

            if len(questions) >= limit:
                break

        return questions[:limit]

    def generate_mcqs(self, n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Generate Multiple Choice Questions (MCQs) with 1 correct option + 3 distractors.
        """
        limit = n if n is not None else self.no_of_questions
        chunks_data = self._extract_chunks_with_context()

        all_unique_chunks = list(dict.fromkeys(
            item["chunk"].strip().title() for item in chunks_data if len(item["chunk"].strip()) >= 3
        ))

        fallback_pool = [
            "Kubernetes", "PostgreSQL", "Docker Container", "REST API", "Redis Cache",
            "CI/CD Pipeline", "Microservices Architecture", "OAuth2 Authentication",
            "TypeScript", "Python AsyncIO", "GraphQL Gateway", "AWS Lambda"
        ]

        mcq_list = []
        seen_stems = set()

        stems = {
            "easy": [
                "Which technology or tool mentioned in your profile relates to: '{snippet}'?",
                "Identify the primary concept highlighted in this context: '{snippet}'?",
                "Which of the following components was utilized in: '{snippet}'?"
            ],
            "medium": [
                "In the context of '{snippet}', which core technology/skill was implemented?",
                "Which component or tool best fulfills the requirement described here: '{snippet}'?",
                "Based on your profile accomplishments, which skill was applied for: '{snippet}'?"
            ],
            "hard": [
                "Which architectural component is centrally responsible for the functionality described in: '{snippet}'?",
                "Given the implementation scenario '{snippet}', which technology was chosen as the solution?",
                "Identify the critical tool/library leveraged in the following engineering outcome: '{snippet}'?"
            ]
        }

        stem_templates = stems.get(self.difficulty, stems["medium"])

        for item in chunks_data:
            correct_ans = item["chunk"].strip().title()
            sentence = item["sentence"].strip()

            if correct_ans.lower() in seen_stems or len(correct_ans) < 3:
                continue

            snippet = sentence
            if len(snippet) > 110:
                snippet = snippet[:107] + "..."

            stem = random.choice(stem_templates).format(snippet=snippet)
            seen_stems.add(correct_ans.lower())

            potential_distractors = [c for c in all_unique_chunks if c.lower() != correct_ans.lower()]
            if len(potential_distractors) < 3:
                potential_distractors.extend([fb for fb in fallback_pool if fb.lower() != correct_ans.lower()])

            distractors = random.sample(potential_distractors, min(3, len(potential_distractors)))
            while len(distractors) < 3:
                distractors.append(f"Alternative Option {len(distractors) + 1}")

            options = [correct_ans] + distractors
            random.shuffle(options)

            correct_letter = chr(65 + options.index(correct_ans))

            mcq_list.append({
                "question": stem,
                "options": options,
                "correct_answer": correct_ans,
                "correct_letter": correct_letter,
                "explanation": f"Source context: \"{sentence}\"",
                "type": "MCQ",
                "difficulty": self.difficulty.capitalize(),
                "topic": correct_ans
            })

            if len(mcq_list) >= limit:
                break

        return mcq_list[:limit]

    def generate(self, question_type: str = "long", n: Optional[int] = None, difficulty: Optional[str] = None) -> Dict[str, Any]:
        """
        Unified method returning both flat and concept-grouped questions with metadata.
        """
        if difficulty:
            self.difficulty = difficulty.lower()

        q_type = (question_type or "long").lower()
        if q_type in ("mcq", "multiple_choice", "quiz"):
            flat_questions = self.generate_mcqs(n)
        elif q_type in ("short", "short_answer", "concept"):
            flat_questions = self.generate_short_answer_questions(n)
        else:
            flat_questions = self.generate_long_answer_questions(n)

        grouped = group_questions_by_concept(flat_questions, self.concepts)

        return {
            "flat_questions": flat_questions,
            "grouped_questions": grouped,
            "concepts": self.concepts,
            "total_count": len(flat_questions),
            "question_type": q_type,
            "difficulty": self.difficulty.capitalize()
        }
