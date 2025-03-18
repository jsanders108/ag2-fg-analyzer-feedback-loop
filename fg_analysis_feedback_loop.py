from typing import Annotated, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from autogen import (
    ConversableAgent,
    UserProxyAgent,
    register_hand_off,
    OnContextCondition,
    AfterWork,
    AfterWorkOption,
    initiate_swarm_chat,
    ContextExpression,
    SwarmResult,
)

import os

from utils import get_openai_api_key
OPENAI_API_KEY = get_openai_api_key()
llm_config = {
    "api_type": "openai", 
    "model": "gpt-4o-mini",
    "parallel_tool_calls": False,
    "cache_seed": None
}

# Feedback Loop pattern for iterative analysis refinement


# Document stage tracking for the feedback loop
class DocumentStage(str, Enum):
    ANALYSIS = "analysis"
    REVIEW = "review"
    REVISION = "revision"
    FINAL = "final" 

# Shared context for tracking document state
shared_context = {
    # Feedback loop state
    "loop_started": False,
    "current_iteration": 0,
    "max_iterations": 3,
    "iteration_needed": True,
    "current_stage": DocumentStage.ANALYSIS,

    # Document data at various stages
    "focus_group_transcripts": "",
    "focus_group_objectives": "",
    "analysis_draft": {},
    "feedback_collection": {},
    "revised_analysis": {},
    "final_report": {},

    # Error state
    "has_error": False,
    "error_message": "",
    "error_stage": ""
}

#  Read Transcripts and Objectives
def read_data(context_variables: dict) -> SwarmResult:
    """Read the transcripts and objectives files and start the analysis feedback loop"""
    # Read transcripts
    with open('data/transcripts.md', 'r') as file:
        transcripts = file.read()
    context_variables['fg_transcripts'] = transcripts
    
    # Read objectives
    with open('data/objectives.md', 'r') as file:
        objectives = file.read()
    context_variables['fg_objectives'] = objectives

    context_variables["loop_started"] = True # Drives OnContextCondition to the next agent
    context_variables["current_stage"] = DocumentStage.ANALYSIS.value # Drives OnContextCondition to the next agent
    context_variables["current_iteration"] = 1
 
    return SwarmResult(
        context_variables=context_variables,
        values=f"Read transcripts and objectives, and started the analysis feedback loop.",
    )



# Analysis Drafting Stage
class AnalysisDraft(BaseModel):
    title: str = Field(..., description="Analysis title")
    content: str = Field(..., description="Full text content of the analysis")

def submit_analysis_draft(
    title: Annotated[str, "Analysis title"],
    content: Annotated[str, "Full text content of the analysis"],
    context_variables: dict[str, Any]
) -> SwarmResult:
    """
    Submit the analysis draft for review
    """
    analysis_draft = AnalysisDraft(
        title=title,
        content=content
    )
    context_variables["analysis_draft"] = analysis_draft.model_dump()
    context_variables["current_stage"] = DocumentStage.REVIEW.value # Drives OnContextCondition to the next agent

    return SwarmResult(
        values="Analysis draft submitted. Moving to review stage.",
        context_variables=context_variables,
    )



# Analysis Feedback Stage
class FeedbackItem(BaseModel):
    feedback: str = Field(..., description="Detailed feedback")
    severity: str = Field(..., description="Severity level of the feedback: minor, moderate, major, critical")
    recommendation: Optional[str] = Field(..., description="Recommended action to address the feedback")

class FeedbackCollection(BaseModel):
    items: list[FeedbackItem] = Field(..., description="Collection of feedback items")
    overall_assessment: str = Field(..., description="Overall assessment of the analysis")
    priority_issues: list[str] = Field(..., description="List of priority issues to address")
    iteration_needed: bool = Field(..., description="Whether another iteration is needed")

def submit_feedback(
    items: Annotated[list[FeedbackItem], "Collection of feedback items"],
    overall_assessment: Annotated[str, "Overall assessment of the analysis"],
    priority_issues: Annotated[list[str], "List of priority issues to address"],
    iteration_needed: Annotated[bool, "Whether another iteration is needed"],
    context_variables: dict[str, Any]
) -> SwarmResult:
    """
    Submit feedback on the document
    """
    feedback = FeedbackCollection(
        items=items,
        overall_assessment=overall_assessment,
        priority_issues=priority_issues,
        iteration_needed=iteration_needed
    )
    context_variables["feedback_collection"] = feedback.model_dump()
    context_variables["iteration_needed"] = feedback.iteration_needed
    context_variables["current_stage"] = DocumentStage.REVISION.value # Drives OnContextCondition to the next agent

    return SwarmResult(
        values="Feedback submitted. Moving to revision stage.",
        context_variables=context_variables,
    )

# Analysis Revision Stage
class RevisedAnalysis(BaseModel):
    title: str = Field(..., description="Analysis title")
    content: str = Field(..., description="Full text content after revision")
    changes_made: Optional[list[str]] = Field(..., description="List of changes made based on feedback")

def submit_revised_analysis(
    title: Annotated[str, "Analysis title"],
    content: Annotated[str, "Full text content after revision"],
    changes_made: Annotated[Optional[list[str]], "List of changes made based on feedback"],
    context_variables: dict[str, Any]
) -> SwarmResult:
    """
    Submit the revised document, which may lead to another feedback loop or finalization
    """
    revised = RevisedAnalysis(
        title=title,
        content=content,
        changes_made=changes_made
    )
    context_variables["revised_analysis"] = revised.model_dump()

    # Check if we need another iteration or if we're done
    if context_variables["iteration_needed"] and context_variables["current_iteration"] < context_variables["max_iterations"]:
        context_variables["current_iteration"] += 1
        context_variables["current_stage"] = DocumentStage.REVIEW.value

        # Update the analysis draft with the revisions for the next review
        context_variables["analysis_draft"] = {
            "title": revised.title,
            "content": revised.content
        } 

        return SwarmResult(
            values=f"Analysis revised. Starting iteration {context_variables['current_iteration']} with another review.",
            context_variables=context_variables,
        )
    else:
        # We're done with revisions, move to final stage
        context_variables["current_stage"] = DocumentStage.FINAL.value # Drives OnContextCondition to the next agent

        return SwarmResult(
            values="Revisions complete. Moving to document finalization.",
            context_variables=context_variables,
        )

    
# Analysis Finalization Stage
class FinalAnalysis(BaseModel):
    title: str = Field(..., description="Final analysis title")
    content: str = Field(..., description="Full text content of the final analysis")

def finalize_analysis(
    title: Annotated[str, "Final analysis title"],
    content: Annotated[str, "Full text content of the final analysis"],
    context_variables: dict[str, Any]
) -> SwarmResult:
    """
    Submit the final analysis and complete the feedback loop
    """
    final = FinalAnalysis(
        title=title,
        content=content
    )
    context_variables["final_analysis"] = final.model_dump()
    context_variables["iteration_needed"] = False

    return SwarmResult(
        values="Analysis finalized. Feedback loop complete.",
        agent=report_recorder_agent,
        context_variables=context_variables,
    )

# Write Report to File Stage
def write_report_to_file(report: str, filename: str) -> SwarmResult:
    """Write the final report to a markdown file in the 'reports' directory."""
    # Create the 'reports' directory if it doesn't exist
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

# Agents for the feedback loop
ingestion_agent = ConversableAgent(
    name="ingestion_agent",
    llm_config=llm_config,
    system_message="You are a helpful assistant that reads the transcripts and objectives files.",
    functions=[read_data]
)

drafting_agent = ConversableAgent(
    name="drafting_agent",
    system_message="""You are the analysis drafting agent responsible for creating the initial draft.

    Your task is to analyze the focus group transcripts and create a first draft of the analysis. 
    Review the content in the context of the focus group objectives. 

    Identify key themes, patterns, and insights. Pay particular attention to how the discussion points relate 
    to the focus group objectives.

    expected_output:
    A comprehensive analysis draft that includes:
    1. Identified key themes and patterns from the focus group transcripts
    2. Insights derived from the discussion, especially those relating to the focus group objectives
    3. Notable trends or unexpected findings
    4. Areas of consensus or disagreement among participants
    5. Potential implications of the findings
    6. Any gaps in the information or areas that may require further investigation
    7. Initial recommendations based on the analysis

    You must call the submit_analysis_draft tool with your draft and that will move on to the review stage.""",
    llm_config=llm_config,
    functions=[submit_analysis_draft]
)

review_agent = ConversableAgent(
    name="review_agent",
    system_message="""You are the analysis review agent responsible for critical evaluation.

    Your task is to carefully review the current analysis draft and provide constructive feedback.
    Compare the analysis to the focus group objectives to ensure alignment and thoroughness. Assess the quality, clarity, and depth of 
    insights provided. Identify any gaps, inconsistencies, or areas where the analysis could be improved.
    
    For the feedback you MUST provide the following:
    1. items: list of feedback items (seen next section for the collection of feedback items)
    2. overall_assessment: Overall assessment of the analysis
    3. priority_issues: List of priority issues to address
    4. iteration_needed: Whether another iteration is needed (True or False)

    For each item within feedback, you MUST provide the following:
    1. feedback: Detailed feedback explaining the issue
    2. severity: Rate as 'minor', 'moderate', 'major', or 'critical'
    3. recommendation: A clear, specific action to address the feedback

    Provide specific feedback with examples and clear recommendations for improvement.
    For each feedback item, rate its severity.

    If this is a subsequent review iteration, also evaluate how well previous feedback was addressed.

    Use the submit_feedback tool when your review is complete, indicating whether another iteration is needed.
    """,
    llm_config=llm_config,
    functions=[submit_feedback]
)

revision_agent = ConversableAgent(
    name="revision_agent",
    system_message="""You are the analysis revision agent responsible for implementing feedback.

    Your task is to revise the analysis based on the feedback provided:
    - Address each feedback item in priority order
    - Make specific improvements to the content, structure, and clarity
    - Ensure the revised analysis still aligns with the original objectives
    - Track and document the changes you make

    Focus on substantive improvements that address the feedback while preserving the analysis' strengths.

    Use the submit_revised_analysis tool when your revisions are complete. The analysis may go through
    multiple revision cycles depending on the feedback.""",
    llm_config=llm_config,
    functions=[submit_revised_analysis]
)

finalization_agent = ConversableAgent(
    name="finalization_agent",
    system_message="""You are the finalization agent responsible for completing the process.

    Your task is to put the finishing touches on the analysis:
    - Review the analysis's revision history
    - Make any final minor adjustments for clarity and polish
    - Ensure the analysis fully satisfies the original objectives
    - Prepare the final report for delivery with proper formatting

    Create a summary of the analysis's revision journey highlighting how it evolved through the process.

    Use the finalize_analysis tool when the analysis is complete and ready for delivery.""",
    llm_config=llm_config,
    functions=[finalize_analysis]
)

report_recorder_agent = ConversableAgent(
    name="report_recorder_agent",
    system_message="""You are the report recorder agent responsible for recording the final report.

    Your task is to convert the final report into markdown format and save it in the 'reports' directory.

    Use the write_report_to_file tool to save the final report in the 'reports' directory.""",
    llm_config=llm_config,
    functions=[write_report_to_file]
)

# User agent for interaction
user = UserProxyAgent(
    name="user",
    code_execution_config=False
)

# Register handoffs for the feedback loop
# Ingestion agent starts the loop
register_hand_off(
    agent=ingestion_agent,
    hand_to=[
        OnContextCondition(
            target=drafting_agent,
            condition=ContextExpression("${loop_started} == True and ${current_stage} == 'analysis'")
        )
    ]
)

# Drafting agent passes to Review agent
register_hand_off(
    agent=drafting_agent,
    hand_to=[
        OnContextCondition(
            target=review_agent,
            condition=ContextExpression("${current_stage} == 'review'")
        )
    ]
)

# Review agent passes to Revision agent
register_hand_off(
    agent=review_agent,
    hand_to=[
        OnContextCondition(
            target=revision_agent,
            condition=ContextExpression("${current_stage} == 'revision'")
        )
    ]
)

# Revision agent passes back to Review agent or to Finalization agent
register_hand_off(
    agent=revision_agent,
    hand_to=[
        OnContextCondition(
            target=finalization_agent,
            condition=ContextExpression("${current_stage} == 'final'")
        ),
        OnContextCondition(
            target=review_agent,
            condition=ContextExpression("${current_stage} == 'review'")
        )
    ]
)

# Finalization agent passes to Report recorder agent
register_hand_off(
    agent=finalization_agent,
    hand_to=[
        AfterWork(report_recorder_agent), 
    ] 
)

# Report recorder agent completes the loop and returns to user
register_hand_off(
    agent=report_recorder_agent,
    hand_to=[
        AfterWork(AfterWorkOption.REVERT_TO_USER)
    ]
)


# Run the feedback loop
def run_feedback_loop_pattern():
    """Run the feedback loop pattern for analysis creation with iterative refinement"""
    print("Initiating Feedback Loop Pattern for Analysis Creation...")

    chat_result, final_context, last_agent = initiate_swarm_chat(
        initial_agent=ingestion_agent,
        agents=[
            ingestion_agent,
            drafting_agent,
            review_agent,
            revision_agent,
            finalization_agent,
            report_recorder_agent
        ],
        messages=f"Please read the focus group transcripts and focus group objectives", 
        context_variables=shared_context,
        user_agent=user,
        max_rounds=30,
        after_work=AfterWork(AfterWorkOption.REVERT_TO_USER)
    )

    if final_context.get("final_analysis"):
        print("Analysis completed successfully!")
        print("\n===== ANALYSIS SUMMARY =====\n")
        print(f"Title: {final_context['final_analysis'].get('title')}")
        print(f"Word Count: {final_context['final_analysis'].get('word_count')}")
        print(f"Iterations: {final_context.get('current_iteration')}")

        print("\n===== FEEDBACK LOOP PROGRESSION =====\n")
        # Show the progression through iterations
        for i in range(1, final_context.get('current_iteration') + 1):
            if i == 1:
                print(f"Iteration {i}:")
                print(f"  Analysis: {'✅ Completed' if 'final_analysis' in final_context else '❌ Not reached'}")
                print(f"  Review: {'✅ Completed' if 'feedback_collection' in final_context else '❌ Not reached'}")
                print(f"  Revision: {'✅ Completed' if 'revised_analysis' in final_context else '❌ Not reached'}")
            else:
                print(f"Iteration {i}:")
                print(f"  Review: {'✅ Completed' if 'feedback_collection' in final_context else '❌ Not reached'}")
                print(f"  Revision: {'✅ Completed' if 'revised_analysis' in final_context else '❌ Not reached'}")

        print(f"Finalization: {'✅ Completed' if 'final_analysis' in final_context else '❌ Not reached'}")

        print("\n===== REVISION HISTORY =====\n")
        for history_item in final_context['final_analysis'].get('revision_history', []):
            print(f"- {history_item}")

        print("\n===== FINAL ANALYSIS =====\n")
        print(final_context['final_analysis'].get('content', ''))

        print("\n\n===== SPEAKER ORDER =====\n")
        for message in chat_result.chat_history:
            if "name" in message and message["name"] != "_Swarm_Tool_Executor":
                print(f"{message['name']}")
    else:
        print("Document creation did not complete successfully.")
        if final_context.get("has_error"):
            print(f"Error during {final_context.get('error_stage')} stage: {final_context.get('error_message')}")

if __name__ == "__main__":
    run_feedback_loop_pattern()