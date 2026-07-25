# Multilingual Voice AI Support Platform

## Product Requirements Document

- **Document type:** Technical Product Requirements
- **Project type:** Production-grade Voice AI portfolio project
- **Primary goal:** Build and deploy a real multilingual Voice AI support system with real telephony, real business integrations, real retrieval, real persistence, real evaluations, and real operational monitoring.

---

## 1. Non-Negotiable Project Rule

This project must not contain dummy or simulated product functionality in the final deployed version.

The final system must use:

- Real inbound and outbound phone calls.
- Real browser-based voice sessions.
- Real speech-to-text and text-to-speech providers.
- Real customer and product records stored in a database.
- Real support documents ingested into the retrieval system.
- Real ticket creation in an actual support or issue-tracking platform.
- Real appointment scheduling through a calendar integration.
- Real message delivery through email or WhatsApp/SMS.
- Real call recordings, transcripts, tool traces, and latency measurements.
- Real authentication, authorization, deployment, monitoring, and failure handling.
- Real evaluation runs against the deployed agent.

Seed data may be created for initial onboarding, but it must be stored, queried, modified, and audited through the same production APIs and databases used by the deployed application. No hard-coded tool responses, fixed transcripts, fake API success messages, or UI-only demonstrations are permitted.

## 2. Product Vision

Build a multilingual Voice AI customer-support platform that allows customers to contact a business through a browser or telephone, explain their issue in English, Hindi, or Hinglish, and receive accurate support from an AI agent.

The agent must be able to:

- Identify the caller.
- Retrieve the caller's real account, product, order, or subscription details.
- Understand the issue and collect missing information.
- Search a real support knowledge base.
- Execute real backend actions through authenticated tools.
- Ask for confirmation before consequential actions.
- Escalate the conversation to a human when required.
- Produce a structured summary for the human support agent.
- Store the entire call lifecycle for replay and evaluation.
- Measure whether the interaction was actually successful.

The project should demonstrate the capabilities expected from an Applied AI Engineer, Voice AI Engineer, Conversational AI Engineer, Forward Deployed Engineer, or AI Platform Engineer.

## 3. Target Use Case

The initial use case is customer support for a real small business, open-source product, SaaS product, or user-owned service.

A valid production use case must have:

- A real support knowledge base.
- Real users or test users with stored identities.
- A real product, order, device, subscription, or service record.
- At least three support workflows.
- At least one workflow that reads data.
- At least one workflow that modifies data.
- At least one workflow that requires explicit user confirmation.
- At least one workflow that can escalate to a human.

Recommended initial workflow categories:

- Account or subscription support.
- Order status and delivery support.
- Product troubleshooting.
- Appointment or service booking.
- Ticket creation and follow-up.

The final domain should be selected based on access to real APIs and data. The architecture must remain domain-independent.

## 4. Product Scope

### 4.1 In Scope

- Browser-based real-time voice conversations.
- Inbound telephone calls.
- Outbound telephone calls with user consent.
- English, Hindi, and Hinglish conversations.
- Streaming speech recognition.
- Streaming speech generation.
- Turn detection and interruption handling.
- Retrieval-augmented generation.
- Tool calling.
- Real backend integrations.
- Authentication and role-based access control.
- Human escalation.
- Call recordings and transcripts.
- Conversation replay.
- Evaluation and regression testing.
- Operational dashboards.
- Cloud deployment.
- Observability and alerting.
- Cost tracking.
- PII handling and retention controls.

### 4.2 Out of Scope for Initial Release

- Training a foundation speech model from scratch.
- Creating a generic no-code Voice AI platform.
- Supporting more than three languages in the first production release.
- Autonomous refunds or financial transactions.
- Emergency, medical, legal, or safety-critical advice.
- Voice cloning without explicit speaker consent.
- Fully replacing human customer-support operations.
- Complex multi-agent systems without a measurable need.
- Building a custom telephony carrier or WebRTC media server.

## 5. Users and Roles

### 5.1 Customer

The customer can:

- Start a browser voice session.
- Call the support number.
- Speak in English, Hindi, or Hinglish.
- Interrupt or correct the agent.
- Request a human agent.
- Confirm or reject actions.
- Receive follow-up information.

### 5.2 Human Support Agent

The support agent can:

- View active and completed calls.
- Read live transcripts.
- View retrieved evidence.
- View tool calls and results.
- Take over an active conversation.
- Receive a structured handoff summary.
- Update ticket status.
- Add notes and final resolution.
- Review agent mistakes.

### 5.3 Support Manager

The manager can:

- Review performance metrics.
- Inspect failed conversations.
- Compare prompt or model versions.
- Review handoff and resolution rates.
- Configure escalation policies.
- Review evaluation reports.
- Monitor provider health and cost.

### 5.4 AI or Platform Engineer

The engineer can:

- Configure providers.
- Deploy agent versions.
- Inspect traces.
- Run regression suites.
- Review latency breakdowns.
- Roll back failed releases.
- Configure alerting and retention.

## 6. Core Functional Requirements

### 6.1 Browser Voice Interface

The browser client must:

- Request microphone permission.
- Join a real-time audio session.
- Stream microphone audio.
- Play streamed agent audio.
- Display live partial and final transcripts.
- Display connection status.
- Allow microphone mute and session termination.
- Show when the user or agent is speaking.
- Support interruption of agent speech.
- Recover from temporary connection failures when possible.
- Display a clear fallback message when recovery is not possible.

**Acceptance criteria:**

- A user can complete an entire support workflow using only voice.
- The transcript reflects both participants.
- The user can interrupt the agent and receive a corrected response.
- The session is persisted after completion.

### 6.2 Telephone Integration

The system must integrate with a real telephony provider.

**Required capabilities:**

- Purchase or connect a real telephone number.
- Accept inbound calls.
- Place outbound calls only to consented test users.
- Stream bidirectional call audio to the Voice AI runtime.
- Receive call lifecycle webhooks.
- Store provider call identifiers.
- Record calls with consent.
- Detect call termination.
- Support DTMF input where required.
- Transfer calls to a real human support number or queue.
- Handle provider errors and call failures.

**Acceptance criteria:**

- A user can call a real number and complete a supported workflow.
- Audio is streamed in both directions.
- The call record, recording, transcript, and outcome are stored.
- Human transfer works for at least one configured destination.
- Failed calls are visible in the dashboard.

### 6.3 Speech-to-Text

The system must use a real streaming speech-to-text provider.

**Requirements:**

- Streaming transcription.
- Partial transcripts.
- Final transcripts.
- Word or utterance timestamps.
- English support.
- Hindi support.
- Hinglish or code-switching support where supported.
- Configurable end-of-turn behaviour.
- Error handling and provider timeout handling.
- Provider latency measurement.
- Transcript confidence metadata where available.

**The system must store:**

- Raw provider events where legally and technically permitted.
- Partial and final transcripts.
- Language information.
- Timing information.
- Errors and retries.
- Provider name and model version.

**Acceptance criteria:**

- Speech is transcribed during the call.
- Partial transcripts appear before the user finishes speaking.
- Final transcripts are stored.
- English, Hindi, and Hinglish test cases are included in evaluation runs.

### 6.4 Text-to-Speech

The system must use a real streaming text-to-speech provider.

**Requirements:**

- Streaming audio generation.
- Low first-audio latency.
- English and Hindi-capable voices.
- Pronunciation handling for names and product terms.
- Immediate cancellation on barge-in.
- Audio generation error handling.
- Provider latency and cost measurement.
- Configurable voice and speaking style.
- Consent-compliant voice selection.

**Acceptance criteria:**

- The agent begins speaking before the complete response is generated.
- TTS stops when the user interrupts.
- The system records first-audio latency.
- The selected voice works consistently across supported languages.

### 6.5 Conversation Orchestrator

The orchestrator must manage the complete support interaction.

**Responsibilities:**

- Maintain conversation state.
- Track current workflow.
- Determine missing information.
- Select tools.
- Validate tool arguments.
- Enforce confirmation requirements.
- Keep spoken responses short and natural.
- Avoid repeating already confirmed information.
- Recover from misunderstandings.
- Trigger escalation.
- Produce a final structured outcome.

**Required conversation states:**

- GREETING
- CONSENT
- CUSTOMER_IDENTIFICATION
- ISSUE_DISCOVERY
- INFORMATION_COLLECTION
- KNOWLEDGE_RETRIEVAL
- ACTION_PROPOSAL
- USER_CONFIRMATION
- TOOL_EXECUTION
- RESOLUTION_CONFIRMATION
- HUMAN_HANDOFF
- COMPLETED
- FAILED

The implementation may use a graph, state machine, or bounded agent loop, but transitions must be logged.

**Acceptance criteria:**

- Every call has a visible state history.
- Consequential tools cannot run without confirmation.
- The agent can recover when a user corrects information.
- The agent stops or escalates after configured failure limits.

### 6.6 Real Customer and Business Data

The system must use a real database and real APIs.

**Minimum entities:**

- Customer.
- Contact method.
- Product, order, subscription, or device.
- Support ticket.
- Appointment or service request.
- Conversation.
- Call.
- Tool execution.
- Knowledge document.
- Evaluation run.
- Agent version.

**Requirements:**

- PostgreSQL as the system of record.
- Database migrations.
- Unique identifiers.
- Created and updated timestamps.
- Audit fields.
- Input validation.
- Authentication for write operations.
- Idempotency for consequential actions.
- Soft deletion or retention rules where applicable.
- No hard-coded tool results.

**Seed records are permitted only when:**

- They are inserted through migration or seed scripts.
- They are stored in the database.
- They can be updated through real APIs.
- The agent retrieves them through authenticated tools.
- The dashboard displays their current state.

### 6.7 Knowledge Base and RAG

The system must ingest real support content.

**Valid content sources:**

- Public product documentation.
- Public help-centre articles.
- User-authored support documents.
- Open-source project documentation.
- User-owned company documentation with permission.
- Real support FAQs created for the chosen product.

**Requirements:**

- Document ingestion pipeline.
- Text extraction.
- Chunking.
- Metadata enrichment.
- Embedding generation.
- Vector storage.
- Hybrid or semantic retrieval.
- Reranking.
- Source tracking.
- Document versioning.
- Re-ingestion on content updates.
- Retrieval logging.
- Grounded answer generation.
- Evidence visibility in the dashboard.

The agent must not invent a support procedure when retrieval confidence is insufficient.

**Acceptance criteria:**

- At least 50 real support documents or articles are ingested.
- Each retrieved answer links back to source content.
- Retrieval results are stored with the conversation.
- Unsupported questions lead to clarification or escalation.
- The evaluation suite contains retrieval-specific tests.

### 6.8 Real Tool Integrations

At least four production integrations must be implemented.

**Required categories:**

1. **Identity or Customer Data** — examples:
   - PostgreSQL customer service.
   - Supabase.
   - Existing CRM API.
   - Shopify customer API.
   - HubSpot API.
2. **Ticketing** — at least one:
   - Jira.
   - Linear.
   - Zendesk.
   - Freshdesk.
   - GitHub Issues for an open-source support use case.
   - The system must create a real ticket and store the external ticket identifier.
3. **Scheduling** — at least one:
   - Google Calendar.
   - Cal.com.
   - Calendly.
   - The system must read real availability and create a real event after user confirmation.
4. **Messaging** — at least one:
   - Gmail.
   - Twilio SMS.
   - WhatsApp Business API.
   - Resend.
   - SendGrid.
   - The system must send a real confirmation or support summary.

**Optional integrations:**

- Shopify.
- WooCommerce.
- Stripe read-only subscription status.
- IoT telemetry API.
- Shipping provider API.
- CRM contact update.

**Acceptance criteria:**

- Every tool returns data from an actual service or production database.
- Tool calls and responses are logged.
- Tool credentials are stored securely.
- Action tools use idempotency keys.
- Tool failures are surfaced to the conversation orchestrator.
- The user is not told that an action succeeded until success is confirmed.

### 6.9 User Confirmation and Safety

**Actions requiring explicit confirmation:**

- Creating an appointment.
- Rescheduling or cancelling an appointment.
- Updating customer contact information.
- Closing a support ticket.
- Sending information to a new contact destination.
- Modifying a subscription or order where enabled.

**Requirements:**

- The agent must repeat the final action details.
- The user must provide an affirmative response.
- Confirmation must be stored.
- The exact tool input must be derived after confirmation.
- Ambiguous confirmations must not trigger execution.
- Repeated tool requests must not create duplicate actions.

**Prohibited autonomous actions:**

- Refund issuance.
- Payment processing.
- Password disclosure.
- Destructive device commands.
- Legal, medical, or emergency decisions.
- Unsupported account ownership changes.

### 6.10 Human Handoff

The system must support real human escalation.

**Requirements:**

- User-requested transfer.
- Policy-triggered transfer.
- Low-confidence transfer.
- Repeated tool failure transfer.
- Repeated misunderstanding transfer.
- Safety-related transfer.
- Human takeover from dashboard.
- Transfer to a real phone number or queue.
- Structured handoff summary.
- Full transcript and evidence available to the human.
- Handoff reason stored.
- Final outcome captured after the human interaction where possible.

**Minimum handoff summary:**

- Customer identity.
- Verified identifiers.
- Primary intent.
- Issue description.
- Important entities.
- Steps already attempted.
- Tools already executed.
- Knowledge sources used.
- Confirmation status.
- Reason for escalation.
- Recommended next action.

**Acceptance criteria:**

- A live telephone call can be transferred to a configured human.
- The human receives the call context.
- The transfer outcome is stored.

### 6.11 Call and Conversation Storage

The system must store:

- Session identifier.
- User identifier.
- Call provider identifier.
- Start and end timestamps.
- Call status.
- Audio recording reference.
- Partial and final transcripts.
- Conversation turns.
- Agent states.
- Model and provider versions.
- Tool calls.
- Tool results.
- Retrieval results.
- User confirmations.
- Handoff events.
- Errors.
- Latency measurements.
- Token and provider usage.
- Estimated cost.
- Final outcome.
- Evaluation results.

The system must support configurable retention.

### 6.12 Operations Dashboard

The dashboard must contain the following views.

**Active Calls**

- Current caller.
- Current language.
- Live transcript.
- Current agent state.
- Current tool execution.
- Current latency.
- Handoff status.
- Human takeover action.

**Completed Calls**

- Recording playback.
- Full transcript.
- Turn-by-turn timeline.
- State transitions.
- Tool calls and results.
- Retrieved evidence.
- Errors.
- Cost.
- Final outcome.
- Human review fields.

**Tickets and Appointments**

- Created tickets.
- External identifiers.
- Ticket status.
- Created appointments.
- Calendar links.
- Related call.

**Knowledge Base**

- Uploaded or synchronised documents.
- Document status.
- Version.
- Chunk count.
- Last indexed time.
- Search and retrieval inspection.

**Agent Versions**

- Prompt version.
- Model configuration.
- STT provider.
- TTS provider.
- Deployment date.
- Evaluation score.
- Active or rolled-back status.

**Analytics**

- Total calls.
- Completed calls.
- Resolved calls.
- Escalation rate.
- Failed-call rate.
- Average handling time.
- p50 and p95 response latency.
- Tool success rate.
- Confirmation compliance.
- Retrieval groundedness.
- Language-wise success rate.
- Cost per call.
- Cost per resolved call.

## 7. Voice-Specific Requirements

### 7.1 Barge-In

When the user speaks while the agent is speaking:

- Detect new user speech.
- Stop or cancel TTS.
- Clear unsent audio.
- Record the interruption event.
- Preserve only the assistant content that was actually played when possible.
- Process the new user utterance.
- Resume the conversation using corrected context.

**Acceptance criteria:**

- The agent stops speaking within a defined interruption threshold.
- The system does not continue playing stale audio.
- The interruption appears in the call timeline.

### 7.2 Turn Detection

The system must distinguish:

- End of sentence.
- Short hesitation.
- Long silence.
- Backchannel.
- User interruption.
- Background speech.
- Abandoned turn.

**Requirements:**

- Configurable endpointing.
- Minimum speech duration.
- Maximum silence threshold.
- Timeout behaviour.
- Per-call logging.
- Test cases for natural pauses.

### 7.3 Latency Tracing

For every turn, measure:

- Speech start.
- Speech end.
- STT first partial.
- STT final.
- LLM request start.
- LLM first token.
- Tool start.
- Tool end.
- TTS request start.
- TTS first audio.
- Audio playback start.
- Total response latency.

The dashboard must expose p50 and p95 values.

### 7.4 Multilingual Behaviour

The agent must:

- Respond in the user's language.
- Support English.
- Support Hindi.
- Support Hinglish.
- Preserve names, numbers, email addresses, dates, and identifiers.
- Ask for spelling or repetition when confidence is low.
- Avoid translating product identifiers.
- Support language change during a call.
- Store detected language per turn where possible.

## 8. Evaluation Requirements

The evaluation platform must test the actual deployed agent.

No evaluation may rely only on manually written expected transcripts.

**Required evaluation methods:**

- Automated text-based simulated callers.
- Audio-based prerecorded test calls.
- Real human test calls.
- Tool-call assertions.
- Retrieval assertions.
- Latency assertions.
- Confirmation-policy assertions.
- Failure-injection tests.
- Prompt and model regression tests.

### 8.1 Required Test Scenarios

- Successful account lookup.
- Unknown caller.
- Incorrect identifier.
- Successful knowledge-based resolution.
- Knowledge not found.
- Successful ticket creation.
- Ticketing provider failure.
- Successful appointment booking.
- Booking without confirmation attempt.
- User changes the selected time.
- User interrupts agent.
- User requests human support.
- Hinglish conversation.
- Slow speaker.
- Long pause.
- Background noise.
- Repeated misunderstanding.
- Telephony disconnect.
- Duplicate tool request.
- Agent provider timeout.
- TTS provider timeout.
- Retrieval with irrelevant documents.
- Prohibited action request.

### 8.2 Evaluation Metrics

**Conversation Outcome**

- Task completion rate.
- Resolution rate.
- Escalation rate.
- Correct escalation rate.
- Average turns to resolution.
- Abandonment rate.

**Agent Quality**

- Tool selection accuracy.
- Tool argument accuracy.
- Confirmation compliance.
- Unsupported claim rate.
- Retrieval groundedness.
- Repetition rate.
- Policy violation rate.

**Voice Quality**

- Time to first transcript.
- Time to final transcript.
- Time to first agent audio.
- End-to-end response latency.
- User interruption success.
- False interruption rate.
- Excessive silence rate.
- Audio failure rate.

**Business Quality**

- Ticket creation success.
- Appointment creation success.
- Duplicate action rate.
- Human handling time after escalation.
- Cost per completed call.
- Cost per resolved call.

## 9. Reliability Requirements

The system must implement:

- Timeouts for every external provider.
- Retries only for safe operations.
- Idempotency for write operations.
- Circuit breakers.
- Provider health checks.
- Graceful call termination.
- Fallback messages.
- Tool failure escalation.
- Database transaction handling.
- Dead-letter or failure queue for asynchronous jobs.
- Structured error logging.
- Alerting for repeated failures.

The system must never claim success before receiving confirmed success from the underlying integration.

## 10. Security and Privacy Requirements

**Required controls:**

- HTTPS and secure WebSocket connections.
- Secret storage outside source code.
- Role-based access control.
- Least-privilege provider credentials.
- Encryption at rest where supported.
- Encryption in transit.
- Call-recording consent.
- PII masking in logs.
- Configurable audio and transcript retention.
- Audit logging.
- Access logging.
- Deletion workflow.
- Export workflow for user data.
- No public exposure of raw recordings.
- No storage of payment credentials.
- No voice cloning without explicit consent.

## 11. Technical Architecture

```
Browser Client / Telephone Network
                |
                v
        Realtime Media Layer
      WebRTC / SIP / WebSocket
                |
                v
          Voice Agent Runtime
   VAD -> STT -> Orchestrator -> TTS
                |
        +-------+--------+
        |                |
        v                v
 Knowledge Retrieval   Tool Gateway
 pgvector / search     Authenticated APIs
        |                |
        +-------+--------+
                |
                v
       Event and Trace Pipeline
                |
      +---------+----------+
      |                    |
      v                    v
 PostgreSQL             Object Storage
 Metadata, state        Audio, exports
      |
      v
 Operations and Evaluation Dashboard
```

## 12. Recommended Technology Stack

**Realtime Voice**

- LiveKit Agents or Pipecat.
- WebRTC for browser sessions.
- SIP or provider media streams for telephony.

**Speech Providers** (at least one real provider for each category)

- STT: Deepgram, OpenAI, Google Cloud Speech-to-Text, or Azure Speech.
- LLM: OpenAI, Anthropic, Google Gemini, or another tool-capable model.
- TTS: ElevenLabs, Cartesia, Deepgram, OpenAI, Azure Speech, or Google Cloud TTS.

**Backend**

- Python.
- FastAPI.
- PostgreSQL.
- pgvector.
- Redis.
- Background worker system.
- Object storage.

**Frontend**

- Next.js.
- TypeScript.
- WebSocket or realtime event subscription.
- Secure authenticated dashboard.

**Real Integrations**

- Ticketing: Jira, Linear, Zendesk, Freshdesk, or GitHub Issues.
- Scheduling: Google Calendar, Cal.com, or Calendly.
- Messaging: Gmail, WhatsApp Business, SMS, Resend, or SendGrid.
- Telephony: Exotel, Twilio, Plivo, or another supported provider.

**Infrastructure**

- Docker.
- AWS ECS, EC2, or Kubernetes.
- RDS PostgreSQL.
- ElastiCache Redis or managed Redis.
- S3.
- CloudWatch, Grafana, or another monitoring stack.
- GitHub Actions.

## 13. Data Model

**Minimum tables:**

- users
- roles
- customers
- customer_contacts
- products_or_services
- customer_products
- support_tickets
- appointments
- conversations
- calls
- conversation_turns
- agent_state_events
- tool_executions
- tool_confirmations
- knowledge_documents
- knowledge_chunks
- retrieval_events
- recordings
- agent_versions
- provider_configs
- evaluation_suites
- evaluation_cases
- evaluation_runs
- evaluation_results
- audit_logs

**Every write action must be traceable to:**

- User.
- Agent version.
- Conversation.
- Tool call.
- Timestamp.
- Confirmation record where required.

## 14. API Requirements

**Required API groups:**

**Authentication**

- Login.
- Logout.
- Refresh token.
- Current user.
- Role validation.

**Customers**

- Create customer.
- Read customer.
- Search customer.
- Update allowed customer fields.
- List customer products or subscriptions.

**Conversations**

- Start conversation.
- Read conversation.
- List conversations.
- Read transcript.
- Read timeline.
- Mark review outcome.

**Calls**

- Create call session.
- Receive telephony webhook.
- Read call.
- Read recording metadata.
- Trigger human transfer.

**Tickets**

- Create ticket.
- Read ticket.
- Update ticket status.
- Link external ticket.

**Appointments**

- Read availability.
- Create appointment.
- Reschedule appointment.
- Cancel appointment.

**Knowledge**

- Add document.
- Synchronise source.
- Re-index document.
- Search knowledge.
- View retrieval event.

**Evaluations**

- Create suite.
- Run suite.
- Read run.
- Compare runs.
- Approve or reject release.

## 15. Deployment Requirements

The system must have:

- Local development environment.
- Staging environment.
- Production demo environment.
- Infrastructure configuration.
- Automated migrations.
- CI checks.
- Automated tests.
- Deployment workflow.
- Rollback workflow.
- Health endpoints.
- Readiness endpoints.
- Provider health reporting.
- Environment-specific secret management.

**The production demo must be accessible through:**

- A public HTTPS browser application.
- A real telephone number.
- A protected operations dashboard.

## 16. Development Phases

### Phase 1: Real Browser Voice Session

**Deliverables:**

- Real WebRTC session.
- Real STT.
- Real LLM.
- Real TTS.
- Transcript persistence.
- Interruption handling.
- Latency tracing.
- Authenticated user session.

**Exit criteria:**

- A user can complete a real voice conversation.
- The full conversation is persisted and replayable.

### Phase 2: Real Knowledge Retrieval

**Deliverables:**

- Real document corpus.
- Ingestion pipeline.
- Embeddings.
- Vector retrieval.
- Reranking.
- Evidence display.
- Retrieval evaluation.

**Exit criteria:**

- The agent answers supported questions using source documents.
- Unsupported questions are escalated or clarified.

### Phase 3: Real Business Integrations

**Deliverables:**

- Customer database.
- Real ticketing integration.
- Real calendar integration.
- Real email, WhatsApp, or SMS integration.
- Authentication and idempotency.
- Confirmation policies.

**Exit criteria:**

- The voice agent creates a real ticket.
- The voice agent creates a real calendar event after confirmation.
- The system sends a real follow-up message.

### Phase 4: Real Telephony

**Deliverables:**

- Real support phone number.
- Inbound calling.
- Bidirectional audio.
- Call recording.
- Provider webhooks.
- Human transfer.
- Phone-based identity lookup.

**Exit criteria:**

- A user can call the number and complete a workflow.
- A call can be transferred to a human.

### Phase 5: Multilingual Production Behaviour

**Deliverables:**

- English.
- Hindi.
- Hinglish.
- Language switching.
- Identifier confirmation.
- Multilingual evaluation cases.

**Exit criteria:**

- Supported workflows complete successfully in all three modes.

### Phase 6: Evaluation and Observability

**Deliverables:**

- Automated evaluation suites.
- Audio test corpus.
- Real human testing.
- Latency dashboards.
- Tool and retrieval evaluations.
- Prompt regression comparison.
- Release gating.

**Exit criteria:**

- Agent versions cannot be promoted without passing minimum quality thresholds.

### Phase 7: Production Hardening

**Deliverables:**

- Provider fallback.
- Retry and timeout policies.
- Circuit breakers.
- PII masking.
- Retention controls.
- Cost monitoring.
- Alerts.
- Load tests.
- Security review.

**Exit criteria:**

- The system survives configured provider and network failure tests.
- No duplicate consequential actions occur.

## 17. Definition of Done

The project is complete only when all of the following are true:

- The browser voice experience is publicly deployed.
- A real phone number reaches the agent.
- English, Hindi, and Hinglish calls work.
- At least 50 real support documents are indexed.
- Customer information is retrieved from a real database or CRM.
- A real support ticket can be created.
- A real appointment can be scheduled.
- A real follow-up message can be sent.
- User confirmation is enforced for consequential actions.
- A live call can be escalated to a real human.
- Calls, recordings, transcripts, tool traces, retrieval traces, and outcomes are stored.
- The operations dashboard displays real production data.
- Automated evaluation suites run against the deployed agent.
- Latency, cost, success rate, and failure metrics are visible.
- Provider failures are handled without false success claims.
- The repository contains deployment, architecture, security, and evaluation documentation.
- The final demo contains no hard-coded tool responses or fake success paths.

## 18. Portfolio Deliverables

The final portfolio must include:

- Public product demo.
- Real support telephone number.
- Source-code repository.
- Architecture document.
- API documentation.
- Database schema.
- Deployment guide.
- Evaluation report.
- Latency and cost report.
- Security and privacy notes.
- Demo video.
- Technical article covering failures and engineering decisions.
- A clear README with screenshots and supported workflows.

## 19. Resume Positioning

Suggested project summary:

> Built and deployed a multilingual Voice AI customer-support platform supporting browser and telephone conversations in English, Hindi, and Hinglish. Integrated streaming STT/TTS, retrieval over real support documentation, authenticated business tools, ticketing, calendar scheduling, user confirmations, human handoff, call replay, and automated voice-agent evaluations. Added end-to-end latency tracing, provider failure handling, observability, and cost tracking for production-style operation.

## 20. Immediate First Milestone

The first milestone is **not** a UI prototype.

It is a real end-to-end browser voice session with:

- Authenticated user.
- Live microphone audio.
- Real streaming STT.
- Real LLM response.
- Real streaming TTS.
- Barge-in.
- Persistent transcript.
- Per-turn latency trace.
- Session replay.
- Deployed staging environment.

Only after this milestone works should knowledge retrieval and business tools be added.
