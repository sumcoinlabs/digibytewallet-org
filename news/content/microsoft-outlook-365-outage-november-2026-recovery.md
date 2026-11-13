---
title: Microsoft Outlook Outage: What Failed, Why Email Was Delayed, and Recovery Status
slug: microsoft-outlook-365-outage-november-2026-recovery
summary: A major Outlook and Microsoft 365 outage disrupted email worldwide on November 12-13, 2026. Microsoft says recovery is progressing.
category: Technology news
image_alt: Original technology illustration showing disrupted email connections among cloud servers and an envelope icon
tags: Microsoft Outlook, Microsoft 365, Exchange Online, email outage, cloud services
image: /news/assets/microsoft-outlook-365-outage-november-2026-recovery-16x9.jpg
image_4x3: /news/assets/microsoft-outlook-365-outage-november-2026-recovery-4x3.jpg
image_square: /news/assets/microsoft-outlook-365-outage-november-2026-recovery-1x1.jpg
published: 2026-11-13T22:09:13Z
---

A widespread disruption to Microsoft Outlook and Exchange Online left users unable to access mailboxes or reliably send and receive email from Thursday, November 12, into Friday, November 13, 2026. The problems reached beyond Outlook because many Microsoft 365 tools depend on the same cloud infrastructure.

Microsoft reported progress restoring service on Friday but warned that some customers could still face intermittent access problems and delayed messages. The company said the incident was a technical failure, **not evidence of a cyberattack or AI-agent activity**.

## What services were affected?

The main disruption involved Exchange Online, the backend that supports many Outlook mailboxes. According to [ABC News](https://abcnews.com/US/outlook-down-microsoft-outage-reported-mail/story?id=138088203), the event affected businesses, schools, governments and healthcare organizations in multiple regions.

An incident report replicated by the [University of Pennsylvania's IT service](https://mailservices.isc.upenn.edu/computing/email/penno365/alerts/ms-incidents.html) described problems accessing mail through Outlook on the web, desktop connections, mobile mail protocols and other Exchange interfaces. Related Microsoft 365 functions could also fail when they relied on mailbox access, including parts of Teams, Copilot and the administrative tools. This does **not** mean every feature of those products was completely unavailable.

## What caused the Microsoft 365 outage?

Microsoft initially reported affected servers becoming unavailable and additional traffic overwhelming the remaining infrastructure. Recovery involved restarting components, changing traffic routing and testing configuration adjustments.

In a statement reported by ABC News on November 13, Microsoft said an issue introduced during an earlier network capacity upgrade surfaced after a more recent network change. The company said the underlying issue had been addressed while restoration continued for remaining customers and regions. The precise chain of failure should not be oversimplified into a claim that a single server or a malicious actor caused the incident.

## Was Outlook restored?

Recovery was progressing by Friday morning, with Microsoft reporting improving mailbox access and email queues returning toward normal levels. Users could nevertheless experience delays as queued messages were processed and connections recovered.

The difference between a restored service and a fully cleared mail queue matters. A person who can sign into Outlook again may still be missing messages that arrive later. Organizations should also check email-dependent automations and workflows before assuming normal operation has resumed.

## Practical steps for affected users

1. Check your organization's [Microsoft 365 service health dashboard](https://admin.microsoft.com/Adminportal/Home#/servicehealth) if you have an administrator account.
2. Avoid repeatedly changing account passwords unless Microsoft or your organization identifies an authentication issue.
3. Confirm whether delayed messages eventually arrived before sending duplicates.
4. For urgent communications, use an independently hosted channel until email delivery is demonstrably reliable.

## What the incident shows

The outage illustrates how organizations can share a common point of failure through a major cloud provider. Resilience requires tested fallback communications and awareness of which tools depend on the same underlying services.

## Sources

- [ABC News: Microsoft Outlook outage and company recovery statement](https://abcnews.com/US/outlook-down-microsoft-outage-reported-mail/story?id=138088203)
- [University of Pennsylvania: Microsoft 365 incident updates](https://mailservices.isc.upenn.edu/computing/email/penno365/alerts/ms-incidents.html)
- [Reuters: Outlook and Teams outage recovery reporting](https://www.reuters.com/technology/microsoft-365-outlook-down-thousands-us-users-downdetector-shows-2026-11-12/)

*Reporting status: compiled November 13, 2026, around 21:45 UTC. Check Microsoft's service dashboard for the latest account-specific status.*
