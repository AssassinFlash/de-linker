<!-- source: https://www.w3.org/WAI/WCAG22/Understanding/interruptions.html
     loadedTime(UTC): 2026-10-17T05:31:53.326Z
     httpStatus: 200
     apifyRun: TrRwuJPIOXuAAY33r (wcc-known-1) -->

# Understanding Success Criterion 2.2.4: Interruptions | WAI

## Understanding [SC 2.2.4](https://w3.org/TR/WCAG22#interruptions) Interruptions (Level AAA)

## In Brief

Goal

Users are not interrupted.

What to do

Let people delay or turn off updates, except in emergencies.

Why it's important

Updates distract and disrupt assistive technology users and people with attention deficits.

Interruptions can be postponed or suppressed by the user, except interruptions involving an [emergency](https://www.w3.org/WAI/WCAG22/Understanding/interruptions.html#dfn-emergency).

## Intent

The intent of this success criterion is to allow users to turn off updates from the author/server except in emergencies. Emergencies would include civil emergency alert messages or any other messages that warn of danger to health, safety, or property, including data loss, loss of connection, etcetera.

This allows access by people with cognitive limitations or attention disorders by enabling them to focus on the content. It also allows users who are blind or have low vision to keep their "viewing" focus on the content they are currently reading.

## Benefits

*   Individuals with attention deficit disorders can focus on content without distraction.
*   Individuals with low vision or who use screen readers will not have content updated while they are viewing it (which can lead to discontinuity and misunderstanding if they start reading in one topic and finish in another).

## Examples

Example 1. Setting user preferences

The preferences page of a web portal includes an option to postpone all updates and alerts until the end of the current session, except for alerts concerning emergencies.

## Techniques

Each item in this section represents a technique or combination of techniques that the Accessibility Guidelines Working Group deems sufficient for meeting this success criterion. A technique may go beyond the minimum requirement of the criterion. There may be other ways of meeting the criterion not covered by these techniques. For information on using other techniques, see [Understanding Techniques for WCAG Success Criteria](https://www.w3.org/WAI/WCAG22/Understanding/understanding-techniques), particularly the "Other Techniques" section.

### Sufficient Techniques

*   [G75: Providing a mechanism to postpone any updating of content](https://www.w3.org/WAI/WCAG22/Techniques/general/G75)
*   [G76: Providing a mechanism to request an update of the content instead of updating automatically](https://www.w3.org/WAI/WCAG22/Techniques/general/G76)
*   [SCR14: Using scripts to make nonessential alerts optional](https://www.w3.org/WAI/WCAG22/Techniques/client-side-script/SCR14)

### Failures

The following are common mistakes that are considered failures of this success criterion by the Accessibility Guidelines Working Group.

*   [F40: Failure due to using meta redirect with a time limit](https://www.w3.org/WAI/WCAG22/Techniques/failures/F40)
*   [F41: Failure of Success Criterion 2.2.1, 2.2.4, and 3.2.5 due to using meta refresh to reload the page](https://www.w3.org/WAI/WCAG22/Techniques/failures/F41)

## Key Terms

emergency

a sudden, unexpected situation or occurrence that requires immediate action to preserve health, safety, or property

## Test Rules

The following are Test Rules for certain aspects of this Success Criterion. It is not necessary to use these particular Test Rules to check for conformance with WCAG, but they are defined and approved test methods. For information on using Test Rules, see [Understanding Test Rules for WCAG Success Criteria](https://www.w3.org/WAI/WCAG22/Understanding/understanding-act-rules.html).

*   [Meta element has no refresh delay](https://www.w3.org/WAI/standards-guidelines/act/rules/bc659a/)
*   [Meta element has no refresh delay (no exception)](https://www.w3.org/WAI/standards-guidelines/act/rules/bisz58/)

[Back to Top](https://www.w3.org/WAI/WCAG22/Understanding/interruptions.html#top)