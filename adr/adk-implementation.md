# Architecture Decision Record (ADR)

## Title

Have switched to using Google's ADK framework, however rather than running it as expected using their Dev, API or Commandline routine its embedded in the core PR/MR workflow.
This structure means we can use the ADKs capabilities and native integration to Vertex, Tracing etc. But we loose the "chat" style development tools for testing interactions.

## Status

Accepted

## Context

The default ADK expects you to deploy your agent as either a chat system or an API. Our requirement is to package the agent as a one shot process wrapped in a docker container to be used as an action in a CI pipeline. Therefore, we do not require the chat style interface.

## Decision

For simplicity, I have embedded the ADK default agent into the workflow.

## Consequences

This means we can't use the dev tools for interacting with the LM and chat interface.

## References

[Agent Runtime](https://google.github.io/adk-docs/runtime/#technical-reference)
