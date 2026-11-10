# Presentation Script: Chapters 3 and 4

## Presenter notes

This is a speaking guide, not a substitute for the approved thesis chapters.
Chapter 3 details that are specific to the study (such as the approved
research design, participant recruitment, consent, and instruments) are
marked in brackets because they were not provided with the project files.
Replace each bracketed item with the exact information in your approved
Chapter 3. Do not invent participants, approvals, or collected results.

The model evaluation and app records currently available for the presentation
are synthetic development examples. Call them synthetic whenever discussing
their counts, dates, screenshots, or metrics.

## Opening

“Good day. I will present the methodology in Chapter 3, followed by the
results and discussion in Chapter 4. I will distinguish the study's approved
methodology from the synthetic examples used to test the current software.”

## Chapter 3: Methodology

### Research design and setting

“This study uses **[insert the exact research design stated in Chapter 3]**.
It focuses on StudentSense, a web application that supports student check-ins
and provides counselor-facing tools. The study was conducted at
**[insert the approved setting and study period]**.”

### Participants and data collection

“The intended participants were **[insert the approved population and
eligibility criteria]**. The target and actual sample sizes were
**[insert approved numbers, if applicable]**. Data were collected using
**[insert the approved instruments and procedure]**. Participation,
confidentiality, consent, and data handling followed **[insert the approved
ethics process and safeguards]**.”

**Presenter check:** If no real participants were recruited or no human data
were collected, say so plainly. Do not describe the local demonstration
accounts as study participants.

### System and model approach

“StudentSense is implemented as a Django web application. Its check-in
captures 20 questionnaire responses. The deployed LightGBM support signal
uses the current check-in answers, while the application's survey rules
produce the displayed check-in result. These are separate outputs. The
support signal is experimental and is not a diagnosis.”

“For software testing, the model training script generated 12,000 randomized
answer patterns and assigned labels using the application's survey scoring
rules. That generated data allowed us to exercise training and prediction
over a larger range of answer combinations. It is not a substitute for
responses collected from real participants or a validated outcome measure.”

### Evaluation and procedures

“The saved model was evaluated on 4,000 additional generated answer patterns
using a different random seed. The test examples were still generated and
labeled by the same rules, so this evaluation checks how well the model
approximates those rules. It does not measure clinical validity or establish
performance with real students.”

“The local interface demonstration uses synthetic accounts and records to
show the check-in, analytics, support, messaging, and appointment workflows.
These records were created for testing and are not observations from the
study.”

### Transition to Chapter 4

“With the methodology established, I will now present the software and model
results. I will identify which results are synthetic demonstrations so they
are not confused with findings from real participants.”

## Chapter 4: Results and Discussion

### Training-label distribution — Figure 1

“Figure 1 shows the labels produced for the 12,000 generated training rows.
Most rows were labeled Moderate, and relatively few were labeled Low. This
imbalance is important: overall accuracy can look high when a model performs
well on the largest class, even if it misses examples from a smaller class.
These proportions come from the generator and scoring rules, not from a
measured student population.”

### Synthetic holdout evaluation — Table 1 and Figure 2

“On 4,000 separately generated test rows, the model achieved 91.7 percent
overall accuracy. However, balanced accuracy was 58.0 percent and macro F1
was 0.623. Figure 2 shows the class-by-class results. The model correctly
classified 3,202 of 3,267 Moderate examples and 463 of 687 High examples, but
only 4 of 46 Low examples. Therefore, the overall accuracy alone gives an
overly favorable summary.”

“These are results of reproducing synthetic rule-based labels. They should
not be presented as evidence that the model accurately assesses students.”

### Model shown in the app — Figure 3

“Figure 3 shows a synthetic student's result page. The survey-rule result and
the model's support signal appear separately. The model also shows
probabilities and questionnaire-area totals. These values illustrate the
interface and the current model output; they are not a diagnosis or a
real student's risk estimate.”

### Synthetic app records — Figure 4

“Figure 4 summarizes generated local check-ins across the demonstration
period. The local database contains 360 check-ins for 10 synthetic student
accounts, scheduled twice per full week across 18 weeks, along with three
synthetic teacher accounts and sample counselor activity. This was created
to test and demonstrate the application; it does not mean that 10 students
used the system for four months.”

### Application screenshots — Figures 5–10

“Figure 5 shows the student check-in form, organized into steps.”

“Figure 6 shows the counselor support dashboard, where sample requests,
referrals, and student check-in summaries can be reviewed.”

“Figure 7 shows a student's analytics page, including check-in count, recent
history, and area scores. The separate next-check-in estimate is an offline
experimental feature and may be unavailable; it is not the final LightGBM
signal discussed earlier.”

“Figure 8 shows the counselor's message list. Its sample conversations are
synthetic and are included only to demonstrate the messaging interface.”

“Figure 9 shows the urgent-support page, populated with generated requests
for interface testing.”

“Figure 10 shows the appointment calendar with generated availability and a
sample booking. It does not document a real appointment.”

### Repeated check-ins and personalization

“Repeated check-ins can help the application display a person's history and
changes over time. However, the current deployed LightGBM model uses only the
20 answers from the current check-in and does not learn from earlier entries.
We therefore cannot claim that an individual model's accuracy improves as
that person checks in more often. That would need a separate longitudinal
model and evaluation on new, appropriately collected data.”

### Summary and limitations

“In summary, the synthetic evaluation confirms that the software can train
and run the current model, but it also reveals weak performance for the Low
class. The interface screenshots demonstrate the application's main
workflows using synthetic data. Neither result establishes real-world
effectiveness. Further evaluation would require an appropriate, approved
dataset, a clearly defined outcome, participant-separated testing, and
independent review.”

## Closing

“That concludes the presentation of Chapters 3 and 4. The current model and
sample records are development and demonstration materials. They should not
be used as a diagnosis or as evidence about real student outcomes. Thank
you.”

## Possible questions

**Why use generated data?**  
“It provides randomized examples for checking the training pipeline and
software behavior. Because the labels are generated from the same scoring
rules, it cannot establish how well the model works with real students.”

**Does repeated use improve prediction accuracy?**  
“Not automatically. The deployed model processes the current check-in only.
Repeated use supports history and trend displays, but any claim of improved
personalized accuracy would need a separate model and longitudinal
validation.”

**Is 91.7 percent accuracy a good result?**  
“Not by itself. The test labels are synthetic and imbalanced. The 58.0
percent balanced accuracy and the Low-class result show why per-class
metrics matter. These are software-test metrics, not validated user
performance.”

**Are the screenshots and four-month records real?**  
“No. The local demonstration accounts, check-ins, messages, referrals, and
appointments were generated for testing and presentation. They are not real
participants or collected study data.”
