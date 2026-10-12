# Preprint draft: the logprob instrument (PLAN_BEYOND_CI D5)

`main.tex` is the draft of the arXiv preprint (cs.MA / cs.CL) that D5 plans after the
`docs/stories/` piece ([the answer that did not depend on the
question](../stories/the-answer-that-did-not-depend-on-the-question.md)). It is a
draft: the author line is the owner's to fill, and nothing has been submitted.

Every number in it comes from the results files the story cites, under
`fast_api_voter/scripts/` (named in the paper's data note). A number changed there is
changed here by hand.

Build it in the TeX Live image (no local TeX needed):

    docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/work -w /work \
      texlive/texlive:latest-medium latexmk -pdf main.tex

The figures are TikZ, drawn from numbers written in the source, so the PDF is never
committed. `latexmk -c` cleans the build files.
