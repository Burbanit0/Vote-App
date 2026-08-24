import random
import numpy as np

# French census data: voting-age population by year of age (18–85).
# Source: INSEE RP 2019, four age-group columns summed per year.
age_data = {
    18: 416343 + 433377 + 395666 + 412560,
    19: 395309 + 410714 + 375286 + 390002,
    20: 385065 + 398993 + 370927 + 384532,
    21: 372131 + 384384 + 357581 + 370258,
    22: 370146 + 381869 + 362301 + 374177,
    23: 360901 + 371731 + 356005 + 367951,
    24: 347002 + 357849 + 346277 + 358614,
    25: 345674 + 356195 + 345575 + 357966,
    26: 362321 + 373660 + 363459 + 376224,
    27: 366486 + 377772 + 372324 + 385366,
    28: 373290 + 384835 + 383355 + 397080,
    29: 374197 + 385034 + 391141 + 405038,
    30: 379875 + 390899 + 395872 + 409842,
    31: 381893 + 392786 + 399849 + 413955,
    32: 387094 + 397979 + 407992 + 422167,
    33: 387604 + 398786 + 406130 + 420790,
    34: 385394 + 396435 + 403783 + 417815,
    35: 380127 + 391214 + 400179 + 414133,
    36: 405212 + 416777 + 423799 + 438390,
    37: 409918 + 421707 + 427819 + 442482,
    38: 415493 + 427643 + 433421 + 448307,
    39: 393900 + 405581 + 409982 + 424441,
    40: 387855 + 399149 + 400285 + 414208,
    41: 392747 + 404816 + 399454 + 413671,
    42: 378560 + 390441 + 389825 + 404350,
    43: 391896 + 404346 + 398442 + 413722,
    44: 413159 + 426173 + 419802 + 435157,
    45: 435027 + 448213 + 444733 + 460384,
    46: 445836 + 459886 + 453714 + 469527,
    47: 443926 + 457822 + 450509 + 466462,
    48: 435014 + 448697 + 442478 + 457896,
    49: 427528 + 441572 + 437448 + 452879,
    50: 420403 + 434971 + 434367 + 450472,
    51: 418677 + 432749 + 431582 + 447421,
    52: 427611 + 441979 + 441391 + 457665,
    53: 428356 + 442828 + 443353 + 459310,
    54: 430748 + 444960 + 448656 + 464153,
    55: 424098 + 438142 + 444809 + 460412,
    56: 408160 + 422099 + 429696 + 445047,
    57: 408160 + 421161 + 430734 + 444896,
    58: 403439 + 416331 + 430410 + 444709,
    59: 398034 + 410415 + 429394 + 442263,
    60: 388186 + 400042 + 420715 + 433635,
    61: 384480 + 395817 + 418514 + 430912,
    62: 379050 + 390345 + 415501 + 427893,
    63: 371791 + 382395 + 412354 + 424094,
    64: 370846 + 381146 + 410242 + 421875,
    65: 361301 + 371165 + 402421 + 413428,
    66: 365439 + 374781 + 407626 + 418007,
    67: 356096 + 364694 + 398247 + 408050,
    68: 366582 + 374817 + 412349 + 422019,
    69: 356693 + 364312 + 404851 + 413673,
    70: 354324 + 361485 + 400690 + 409072,
    71: 343241 + 350179 + 393058 + 400876,
    72: 320586 + 327085 + 371293 + 378561,
    73: 236900 + 242793 + 279240 + 286325,
    74: 228830 + 234112 + 272775 + 279055,
    75: 219772 + 224687 + 263648 + 269401,
    76: 199977 + 204674 + 242996 + 249057,
    77: 173672 + 177799 + 216640 + 221914,
    78: 175051 + 179151 + 225878 + 231318,
    79: 178422 + 182015 + 234807 + 239598,
    80: 168374 + 171854 + 227972 + 232663,
    81: 157797 + 160969 + 221619 + 226088,
    82: 150275 + 153145 + 218414 + 222853,
    83: 136476 + 139041 + 209883 + 213902,
    84: 129598 + 131872 + 207254 + 210980,
    85: 114789 + 116712 + 192418 + 195596,
}

_total_population = sum(age_data.values())
_age_probabilities = [count / _total_population for count in age_data.values()]
_ages = list(age_data.keys())


def sample_age() -> int:
    return int(random.choices(_ages, weights=_age_probabilities, k=1)[0])


def sample_region() -> str:
    return str(np.random.choice(["urban", "suburban", "rural"], p=[0.8, 0.15, 0.05]))


def sample_income() -> str:
    income_score = np.random.gamma(shape=2, scale=0.2)
    if income_score < 0.3:
        return "low"
    elif income_score < 0.7:
        return "middle"
    return "high"


def sample_likelihood_to_vote(age: int) -> float:
    base = 0.5
    age_effect = min(age / 100, 0.4)
    income_effect = 0.1 if sample_income() == "high" else 0
    return base + age_effect + income_effect


def sample_employment_status() -> str:
    return random.choices(
        population=["employed", "unemployed", "self_employed", "retired"],
        weights=[0.6, 0.1, 0.1, 0.2],
        k=1,
    )[0]


def sample_family_status() -> str:
    return random.choices(
        population=["single", "with_children", "retired"],
        weights=[0.3, 0.4, 0.3],
        k=1,
    )[0]


def sample_ethnicity_immigration() -> str:
    return random.choices(
        population=["native", "immigrant"],
        weights=[0.8, 0.2],
        k=1,
    )[0]


def sample_religion() -> str:
    return random.choices(
        population=["religious", "non_religious"],
        weights=[0.6, 0.4],
        k=1,
    )[0]


def sample_gender() -> str:
    return str(np.random.choice(["male", "female"], p=[0.49, 0.51]))


def sample_education(age: int) -> str:
    if age < 22:
        return str(np.random.choice(["high_school", "bachelor"], p=[0.7, 0.3]))
    if age < 25:
        return str(np.random.choice(["high_school", "bachelor", "master"], p=[0.3, 0.6, 0.1]))
    if age < 30:
        return str(np.random.choice(
            ["high_school", "bachelor", "master", "phd"], p=[0.2, 0.4, 0.35, 0.05]
        ))
    if age < 40:
        return str(np.random.choice(
            ["high_school", "bachelor", "master", "phd"], p=[0.2, 0.4, 0.3, 0.1]
        ))

    base_probs = {"none": 0.1, "high_school": 0.4, "bachelor": 0.3, "master": 0.15, "phd": 0.05}

    if age < 60:
        multipliers = {"none": 0.7, "high_school": 0.9, "bachelor": 1.1, "master": 1.2, "phd": 1.3}
    else:
        multipliers = {"none": 2.0, "high_school": 1.3, "bachelor": 0.7, "master": 0.5, "phd": 0.3}

    adjusted = {k: base_probs[k] * multipliers[k] for k in base_probs}
    total = sum(adjusted.values())
    probs = [v / total for v in adjusted.values()]
    return str(np.random.choice(list(adjusted.keys()), p=probs))
