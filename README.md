# AG2: Iterative Feedback Loop for Focus Group Transcript Analysis with an Agent Swarm

## Project Objective
This project demonstrates the power of AG2 through an innovative iterative feedback loop designed for refining focus group transcript analysis. By incorporating multiple cycles of drafting, review, and revision, the system produces a polished and actionable final report. The primary goals are:

- **Automate Focus Group Analysis:** Generate an initial analysis draft from raw focus group data.
- **Iterative Refinement:** Utilize repeated feedback and revision cycles to enhance clarity, accuracy, and depth of insights.
- **Deliver a Comprehensive Report:** Produce a well-structured markdown report that communicates key findings and recommendations.

## Focus Group Background
The project simulates a focus group discussion centered on launching a premium product: **white strawberries**. The transcripts capture detailed participant feedback on various aspects such as product features, user experience, and brand perception.

**Focus Group Transcript File:**  
[`data/transcripts.md`](https://github.com/jsanders108/ag2-fg-analyzer-feedback-loop/blob/main/data/transcripts.md)

**Focus Group Objectives File:**  
[`data/objectives.md`](https://github.com/jsanders108/ag2-fg-analyzer-feedback-loop/blob/main/data/objectives.md)

## Project Implementation

### Iterative Feedback Loop
The core of this project is an iterative feedback loop that ensures a high-quality analysis. Key stages include:

- **Drafting Stage:** An initial draft is generated from the transcripts and objectives.
- **Review Stage:** Detailed feedback is collected to identify gaps and opportunities for improvement.
- **Revision Stage:** The analysis draft is updated based on the feedback, with the cycle repeating until quality standards are met.
- **Finalization Stage:** The final analysis is produced and then converted into a markdown report.

The system uses a shared context to track document state, iterations, and the current stage. For example, the `read_data` function initializes the process:

```python
def read_data(context_variables: dict) -> SwarmResult:
    with open('data/transcripts.md', 'r') as file:
        transcripts = file.read()
    context_variables['fg_transcripts'] = transcripts
    
    with open('data/objectives.md', 'r') as file:
        objectives = file.read()
    context_variables['fg_objectives'] = objectives

    context_variables["loop_started"] = True
    context_variables["current_stage"] = DocumentStage.ANALYSIS.value
    context_variables["current_iteration"] = 1
    return SwarmResult(context_variables=context_variables, values="Read transcripts and objectives.")
```

Other stage-specific functions manage the transitions between phases. For instance, the `submit_analysis_draft` function records the initial draft and advances the process:

```python
def submit_analysis_draft(title: str, content: str, context_variables: dict) -> SwarmResult:
    analysis_draft = {
        "title": title,
        "content": content
    }
    context_variables["analysis_draft"] = analysis_draft
    context_variables["current_stage"] = DocumentStage.REVIEW.value
    return SwarmResult(
        values="Analysis draft submitted. Moving to review stage.",
        context_variables=context_variables,
    )
```

After several iterations of drafting, reviewing, and revising, the process culminates with the finalization of the analysis. The `finalize_analysis` function locks in the final version and prepares it for report generation:

```python
def finalize_analysis(title: str, content: str, context_variables: dict) -> SwarmResult:
    final_analysis = {
        "title": title,
        "content": content
    }
    context_variables["final_analysis"] = final_analysis
    context_variables["iteration_needed"] = False
    return SwarmResult(
        values="Analysis finalized. Feedback loop complete.",
        context_variables=context_variables,
    )
```

### Agent Workflow & Handoffs
Specialized agents work sequentially through ingestion, drafting, review, revision, finalization, and report recording. Conditional handoffs based on the current stage ensure that the process moves seamlessly from one phase to the next.

Another example is the `write_report_to_file` function, which converts the final analysis into a markdown report and writes it to file:

```python
def write_report_to_file(report: str, filename: str) -> SwarmResult:
    reports_dir = os.path.join(os.getcwd(), "reports")
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, 'w') as f:
        f.write(report)
    
    return SwarmResult(
        values=f"Report written to {filepath}",
        context_variables={}
    )
```

## Output Showcase

### Focus Group Analysis Final Report

#### 1. Identified Key Themes and Patterns
Based on the transcripts, several key themes emerged:

- **User Experience:** Participants discussed their interactions with the product/service, highlighting both ease of use and areas needing improvement.
- **Brand Perception:** Feedback revealed strong trust in the brand alongside constructive criticism relative to competitors.
- **Product Features:** There were suggestions to enhance functionality, such as customizable reporting features.

#### 2. Insights Derived from the Discussion
- **Balanced Evaluations:** While the product/service was generally well-regarded, specific improvements were identified to drive higher satisfaction.
- **Emotional Connection:** The discussions highlighted a strong brand loyalty paired with areas for strategic enhancement.
- **Data-Driven Feedback:** Both qualitative and quantitative feedback were used to pinpoint actionable insights.

#### 3. Notable Trends or Unexpected Findings
- **High Loyalty:** Despite noted challenges, many participants expressed consistent loyalty.
- **Sustainability Focus:** A significant interest in sustainability practices was evident, with participants favoring eco-friendly brands.
- **Diverse Opinions:** Although there was consensus on the value of responsive customer service, opinions varied regarding feature enhancements.

#### 4. Areas of Consensus or Disagreement
- **Consensus:** There was strong approval for excellent customer service.
- **Disagreement:** Participants offered varied opinions on which new features should be prioritized, suggesting a mix of preferences for customization versus simplicity.

#### 5. Potential Implications of the Findings
- **Feature Enhancements:** Addressing issues like loading times could lead to marked improvements in user satisfaction.
- **Strategic Communications:** Emphasizing sustainability in marketing may resonate strongly with consumers.
- **Further Research:** Additional studies, such as follow-up focus groups or surveys, could refine product development and marketing strategies.

#### 6. Final Recommendations
- **Immediate Updates:** Implement targeted improvements within the next 3 months, tracking progress through user satisfaction surveys.
- **Sustainability Campaign:** Launch a focused marketing campaign to highlight eco-friendly initiatives, monitoring success via engagement metrics.
- **Additional Research:** Conduct further studies in the next 6 months to deepen understanding of feature priorities and customer loyalty.

## Conclusion
This project illustrates how an iterative feedback loop powered by AG2 can transform raw focus group data into a highly refined and actionable report. The system's modular design and dynamic agent handoffs facilitate a thorough review and revision process, ensuring that the final output is both comprehensive and strategically valuable for market research.
