# Model Training and SHAP Development Plan

## Purpose

Develop a model that predicts student academic burnout using custom intake information and a validated MBI-SS outcome measure. Use SHAP to explain the factors behind each prediction.

## 1. Finalize the survey

Collect two types of information in the same intake:

- **Custom intake items:** workload, sleep, study habits, social media use, deadlines, class load, mood and energy, exercise, and sleep consistency.
- **MBI-SS items:** items measuring exhaustion, cynicism, and academic efficacy.

The MBI-SS should be administered and scored according to the official instrument instructions. Permission or licensing requirements should also be confirmed before research data collection.

## 2. Prepare the dataset

For each completed intake:

1. Store the custom intake responses.
2. Calculate the MBI-SS subscale scores:
   - exhaustion
   - cynicism
   - academic efficacy
3. Define the target for the model.
4. Check the data for missing, invalid, or duplicate responses.
5. Remove identifying information from the modeling dataset where possible.

The custom intake responses will be used as the model features. The MBI-SS result will be used as the target because it provides the validated outcome measure.

## 3. Define the prediction task

Choose one prediction task before training:

- **Classification:** predict a burnout-risk category such as low, moderate, or high.
- **Regression:** predict a continuous MBI-SS subscale score or combined research score.

Classification is easier to display in the StudentSense application. Regression can provide more detailed research results. The selected approach and category thresholds must be documented and justified.

## 4. Split the data

Divide the dataset into separate groups:

- **Training data:** used to teach LightGBM.
- **Validation data:** used to adjust model settings.
- **Test data:** used once at the end to measure final performance.

The test data must remain separate during model development. If the dataset is small, use cross-validation and report the method clearly.

## 5. Train the LightGBM model

1. Select the custom intake features.
2. Use the MBI-SS target scores or categories.
3. Train a LightGBM classification or regression model.
4. Adjust model settings using the training and validation data.
5. Apply methods such as early stopping or regularization to reduce overfitting.
6. Save the final trained model and the feature-processing steps.

The first model should be treated as a baseline. Further improvements should only be made after recording the baseline results.

## 6. Evaluate the model

Use measures that match the prediction task.

For classification, report:

- accuracy
- precision
- recall
- F1-score
- confusion matrix
- ROC-AUC, where appropriate

For regression, report:

- mean absolute error
- root mean squared error
- R-squared

The evaluation should also consider whether the model performs consistently across relevant student groups. The model should support research and early identification, not replace professional counseling assessment.

## 7. Add SHAP explanations

Apply SHAP after training and evaluation:

1. Load the final LightGBM model.
2. Pass the test data to the SHAP explainer.
3. Calculate SHAP values for the predictions.
4. Identify the features with the largest contributions.
5. Record whether each feature increased or decreased the predicted risk or score.
6. Produce both overall and individual explanations.

### Overall explanation

Use a SHAP summary or feature-importance plot to show which factors have the greatest influence across the dataset.

### Individual explanation

For each student, show the main factors contributing to the prediction. For example, the explanation may indicate that workload and poor sleep increased the predicted risk, while stronger study habits reduced it.

SHAP explanations describe model behavior. They do not prove that a factor directly causes academic burnout.

## 8. Connect the results to StudentSense

The application can use the model output to:

- display the predicted risk level
- show a short explanation of the main contributing factors
- provide general recommendations related to those factors
- encourage counselor contact for moderate- and high-risk students

Counselor contact should be presented as support and referral, not as an automatic diagnosis or emergency assessment.

## 9. Research reporting

Document the following in the paper:

- survey structure and MBI-SS administration
- participant sample and data collection process
- feature definitions and preprocessing
- MBI-SS scoring method
- LightGBM model type and settings
- train, validation, and test procedure
- evaluation metrics and results
- SHAP explanation method and plots
- privacy, consent, licensing, and ethical safeguards
- limitations, including sample size and self-reported data

## Simple workflow

```text
Custom intake items + MBI-SS responses
                |
                v
       Clean and prepare data
                |
                v
  Custom items = features, MBI-SS = target
                |
                v
       Train and evaluate LightGBM
                |
                v
          Calculate SHAP values
                |
                v
 Explain predictions and provide support
```

## Expected final outcome

The completed system will use research-informed custom intake data to predict an MBI-SS-based academic burnout outcome. LightGBM will provide the prediction, while SHAP will explain the main factors influencing each result. The output will support student self-awareness and timely counselor contact without presenting the system as a clinical diagnostic tool.
