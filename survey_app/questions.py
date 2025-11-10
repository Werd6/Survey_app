from typing import TypedDict


class QuestionData(TypedDict):
    text: str
    contradicts: list[int]  # 0-based indices of questions this contradicts
    requires: list[int]  # 0-based indices of questions this requires


QUESTION_SETS: dict[str, list[QuestionData]] = {
    "Superheroes": [
        {
            "text": "The best superhero is always the most powerful superhero",
            "contradicts": [1, 6],  # Q2 (Intelligence matters more), Q7 (Humor matters more)
            "requires": [],
        },
        {
            "text": "Intelligence matters more than power when deciding the best superhero",
            "contradicts": [0],  # Q1 (Best = most powerful)
            "requires": [],
        },
        {
            "text": "Batman is the best superhero because he has no superpowers",
            "contradicts": [3, 4],  # Q4 (No superpowers = can't be best), Q5 (Spider-Man > Batman)
            "requires": [],
        },
        {
            "text": "A superhero without superpowers can never be the best",
            "contradicts": [2],  # Q3 (Batman is best)
            "requires": [],
        },
        {
            "text": "Spider-Man is a better hero than Batman",
            "contradicts": [2],  # Q3 (Batman is best)
            "requires": [],
        },
        {
            "text": "Superman is stronger than Spider-Man, so he is the best superhero",
            "contradicts": [],
            "requires": [0],  # Requires Q1 (Best = most powerful)
        },
        {
            "text": "Humor makes a superhero better than power does",
            "contradicts": [0],  # Q1 (Best = most powerful)
            "requires": [],
        },
        {
            "text": "Serious superheroes are better than funny ones",
            "contradicts": [],
            "requires": [],
        },
        {
            "text": "A superhero is only a hero if they refuse to kill",
            "contradicts": [9],  # Q10 (Killing can still be hero)
            "requires": [],
        },
        {
            "text": "A superhero who kills can still be considered a hero",
            "contradicts": [8],  # Q9 (Must refuse to kill)
            "requires": [],
        },
    ],
    "Food": [
        {
            "text": "The best food is always the most nutritious",
            "contradicts": [1, 4, 6],  # Q2 (Taste matters more), Q5 (Dessert is better), Q7 (Comfort food is better)
            "requires": [],
        },
        {
            "text": "Taste matters more than nutrition when deciding the best food",
            "contradicts": [0],  # Q1 (Best = most nutritious)
            "requires": [],
        },
        {
            "text": "Pizza is the best food in the world",
            "contradicts": [3],  # Q4 (No food with vegetables can be best)
            "requires": [],
        },
        {
            "text": "No food with vegetables on it can be the best",
            "contradicts": [2, 7],  # Q3 (Pizza is best), Q8 (Healthy food is better)
            "requires": [],
        },
        {
            "text": "Dessert is better than any main course",
            "contradicts": [0, 5],  # Q1 (Best = nutritious), Q6 (Ice cream too unhealthy)
            "requires": [],
        },
        {
            "text": "Ice cream is too unhealthy to be considered the best food",
            "contradicts": [4, 6],  # Q5 (Dessert is better), Q7 (Comfort food is better)
            "requires": [],
        },
        {
            "text": "Comfort food is better than healthy food",
            "contradicts": [0, 7],  # Q1 (Best = nutritious), Q8 (Healthy food is better)
            "requires": [],
        },
        {
            "text": "Healthy food is better than comfort food",
            "contradicts": [6],  # Q7 (Comfort food is better)
            "requires": [],
        },
        {
            "text": "The best food must be enjoyed by most people in the world",
            "contradicts": [9],  # Q10 (Best can be hated by most)
            "requires": [],
        },
        {
            "text": "The best food can be considered the best even if most people hate it",
            "contradicts": [8],  # Q9 (Must be enjoyed by most)
            "requires": [],
        },
    ],
}



