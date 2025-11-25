# .NET Migration Guide

This document provides resources and guidance for implementing this clinic scheduler system in .NET using Microsoft Agent Framework.

## Overview

This repository demonstrates a Python implementation using:
- **Handoff Orchestration** (Supervisor routing to specialized agents)
- **Sequential Orchestration** (Multi-step booking verification flow)
- **Azure Foundry** for model hosting

The same patterns are fully supported in .NET with the Microsoft Agent Framework.

---

## 📚 Essential .NET Resources

### Getting Started

| Resource | Description |
|----------|-------------|
| [.NET Agent Framework README](https://github.com/microsoft/agent-framework/tree/main/dotnet/README.md) | Main entry point for .NET developers |
| [Agent Samples](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/GettingStarted/Agents/README.md) | Complete agent examples with step-by-step tutorials |
| [Workflow Samples](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/GettingStarted/Workflows) | Multi-agent orchestration patterns |
| [Official Documentation](https://learn.microsoft.com/agent-framework/overview/agent-framework-overview) | Microsoft Learn documentation |

---

## 🏥 Healthcare/Booking Relevant Samples

### 1. Sequential Orchestration
**Perfect for multi-step booking flows (Emirates ID → Availability → Booking)**

```
📂 dotnet/samples/GettingStarted/Workflows/_Foundational/04_AgentWorkflowPatterns/Program.cs
```

**Key Code:**
```csharp
// Build sequential workflow: step1 -> step2 -> step3
var workflow = AgentWorkflowBuilder.BuildSequential(
    verificationAgent,
    availabilityAgent,
    bookingAgent
);

// Run workflow
await foreach (var result in workflow.RunAsync(userInput))
{
    // Process results
}
```

**Use Case:** Enforce 5-step booking process where each step must complete before next

---

### 2. Handoff Orchestration
**Perfect for dynamic routing (like your Supervisor agent)**

```
📂 dotnet/samples/GettingStarted/Workflows/_Foundational/04_AgentWorkflowPatterns/Program.cs
```

**Key Code:**
```csharp
// Create triage agent that routes to specialists
var workflow = AgentWorkflowBuilder.CreateHandoffBuilderWith(supervisorAgent)
    .WithHandoffs(supervisorAgent, [ragAgent, bookingAgent])
    .Build();
```

**Use Case:** Route user queries to appropriate agent based on intent (info vs booking)

---

### 3. Human-in-the-Loop (HITL)
**Perfect for approval workflows and confirmations**

```
📂 dotnet/samples/AzureFunctions/05_AgentOrchestration_HITL/
```

**Key Features:**
- External approval events
- Timeout handling
- Manager approval gates
- Patient confirmation steps

**Use Case:** Require manager approval for VIP appointments or patient confirmation before booking

---

## 🚀 Quick Start Examples

### Creating a Basic Agent

```csharp
// From: dotnet/samples/GettingStarted/Agents/Agent_Step01_Running/Program.cs

using Azure.AI.OpenAI;
using Azure.Identity;
using Microsoft.Agents.AI;
using OpenAI;

var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT")!;
var deploymentName = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOYMENT_NAME") ?? "gpt-4o-mini";

AIAgent agent = new AzureOpenAIClient(
    new Uri(endpoint),
    new AzureCliCredential())
    .GetChatClient(deploymentName)
    .CreateAIAgent(
        instructions: "You manage clinic appointments...",
        name: "BookingAgent"
    );

// Run agent
Console.WriteLine(await agent.RunAsync("Book an appointment"));
```

---

### Adding Function Tools

```csharp
// From: dotnet/samples/GettingStarted/Agents/Agent_Step03_UsingFunctionTools/

[Description("Validates Emirates ID")]
static string ValidateEmiratesId(
    [Description("Last 5 digits of Emirates ID")] string last5Digits)
{
    if (last5Digits.Length == 5 && last5Digits.All(char.IsDigit))
        return $"✓ Emirates ID verified (ending in {last5Digits})";
    return "✕ Invalid format. Please provide exactly 5 digits.";
}

AIAgent agent = chatClient.CreateAIAgent(
    name: "VerificationAgent",
    instructions: "You verify patient identity...",
    tools: [
        AIFunctionFactory.Create(ValidateEmiratesId),
        AIFunctionFactory.Create(VerifyPhoneNumber),
        AIFunctionFactory.Create(CheckAvailability)
    ]
);
```

---

### Sequential Workflow Pattern

```csharp
// From: dotnet/samples/GettingStarted/Workflows/_Foundational/04_AgentWorkflowPatterns/

// Step 1: Create specialized agents
ChatClientAgent verificationAgent = new(
    chatClient,
    name: "VerificationAgent",
    instructions: "Step 1: Verify Emirates ID and phone number"
);

ChatClientAgent availabilityAgent = new(
    chatClient,
    name: "AvailabilityAgent", 
    instructions: "Step 2: Check doctor availability"
);

ChatClientAgent bookingAgent = new(
    chatClient,
    name: "BookingAgent",
    instructions: "Step 3: Book the appointment"
);

// Step 2: Build sequential workflow
var workflow = AgentWorkflowBuilder.BuildSequential(
    verificationAgent,
    availabilityAgent,
    bookingAgent
);

// Step 3: Run workflow
var messages = new List<ChatMessage> { new(ChatRole.User, "Book appointment") };
await foreach (var output in workflow.RunAsync(messages))
{
    Console.WriteLine($"Step complete: {output}");
}
```

---

### Handoff Workflow Pattern

```csharp
// From: dotnet/samples/GettingStarted/Workflows/_Foundational/04_AgentWorkflowPatterns/

// Create supervisor (triage) agent
ChatClientAgent supervisorAgent = new(
    chatClient,
    instructions: "Route to RAG agent for info queries, Booking agent for appointments",
    name: "SupervisorAgent"
);

// Create specialist agents
ChatClientAgent ragAgent = new(chatClient, "Answer clinic info questions", "RAGAgent");
ChatClientAgent bookingAgent = new(chatClient, "Handle appointments", "BookingAgent");

// Build handoff workflow
var workflow = AgentWorkflowBuilder.CreateHandoffBuilderWith(supervisorAgent)
    .WithHandoffs(supervisorAgent, [ragAgent, bookingAgent])
    .WithHandoffs([ragAgent, bookingAgent], supervisorAgent) // Allow return to supervisor
    .Build();

// Run with conversation
List<ChatMessage> messages = [new(ChatRole.User, "What are your hours and book me an appointment?")];
await foreach (var output in workflow.RunAsync(messages))
{
    // Handle output
}
```

---

## 🏗️ Production Deployment

### Azure Functions Hosting

```
📂 dotnet/samples/AzureFunctions/
```

| Sample | Description |
|--------|-------------|
| **01_SingleAgent** | Basic HTTP-triggered agent hosting |
| **02_AgentOrchestration_Chaining** | Sequential agent calls with Durable Functions |
| **03_AgentOrchestration_Concurrency** | Parallel agent execution |
| **05_AgentOrchestration_HITL** | Human-in-the-loop approvals |
| **06_LongRunningTools** | Background processes for MCP tools |

**Key Features:**
- Durable orchestration for long-running workflows
- HTTP endpoints for agent invocation
- Status query APIs
- External event handling (for approvals)

---

### Dependency Injection

```csharp
// From: dotnet/samples/GettingStarted/Agents/Agent_Step09_DependencyInjection/

var builder = Host.CreateApplicationBuilder(args);

// Register chat client
builder.Services.AddKeyedChatClient("AzureOpenAI", (sp) =>
    new AzureOpenAIClient(new Uri(endpoint), new AzureCliCredential())
        .GetChatClient(deploymentName)
        .AsIChatClient()
);

// Register agent
builder.Services.AddSingleton<AIAgent>((sp) =>
    new ChatClientAgent(
        chatClient: sp.GetRequiredKeyedService<IChatClient>("AzureOpenAI"),
        options: sp.GetRequiredService<ChatClientAgentOptions>()
    )
);

var host = builder.Build();
await host.RunAsync();
```

---

## 🔗 Azure Foundry Integration

### Using Foundry Agents

```
📂 dotnet/samples/GettingStarted/FoundryAgents/
```

```csharp
// From: FoundryAgents_Step01.2_Running/Program.cs

using Azure.AI.Projects;
using Azure.Identity;
using Microsoft.Agents.AI;

string endpoint = Environment.GetEnvironmentVariable("AZURE_FOUNDRY_PROJECT_ENDPOINT")!;
string deploymentName = Environment.GetEnvironmentVariable("AZURE_FOUNDRY_PROJECT_DEPLOYMENT_NAME") ?? "gpt-4o-mini";

// Get Foundry client
AIProjectClient aiProjectClient = new(new Uri(endpoint), new AzureCliCredential());

// Create agent definition
AgentDefinition agentDefinition = new()
{
    Name = "BookingAgent",
    Instructions = "You manage clinic appointments...",
    Model = deploymentName
};

// Create the agent
AgentVersion agentVersion = await aiProjectClient.CreateAgentAsync(agentDefinition);
AIAgent agent = aiProjectClient.GetAIAgent(agentVersion);

// Use the agent
AgentThread thread = agent.GetNewThread();
Console.WriteLine(await agent.RunAsync("Book appointment", thread));
```

---

## 📖 Complete Examples

### Example 1: Marketing Campaign (Similar to Your Booking Flow)

```
📂 dotnet/samples/GettingStarted/Workflows/Declarative/Marketing/Program.cs
```

**Structure:** Analyst → Writer → Editor (3 sequential agents)  
**Similar to:** Verification → Availability → Booking

---

### Example 2: Customer Support with Handoffs

```
📂 dotnet/samples/GettingStarted/Workflows/_Foundational/04_AgentWorkflowPatterns/Program.cs
```

**Structure:** Triage → Specialist agents (Handoff pattern)  
**Similar to:** Supervisor → RAG/Booking agents

---

### Example 3: Azure Functions with HITL

```
📂 dotnet/samples/AzureFunctions/05_AgentOrchestration_HITL/
```

**Features:**
- Durable Functions orchestration
- HTTP endpoints for starting workflow
- External approval events
- Timeout handling

---

## 🎯 Recommended Learning Path

### For Your Booking System in .NET:

1. **Start Here:** [Agent_Step01_Running](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/GettingStarted/Agents/Agent_Step01_Running)
   - Create basic agent
   - Connect to Azure OpenAI

2. **Add Tools:** [Agent_Step03_UsingFunctionTools](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/GettingStarted/Agents/Agent_Step03_UsingFunctionTools)
   - Add Emirates ID validation
   - Add availability checking
   - Add booking functions

3. **Sequential Flow:** [04_AgentWorkflowPatterns](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/GettingStarted/Workflows/_Foundational/04_AgentWorkflowPatterns)
   - Build 3-step verification workflow
   - Enforce step order

4. **Handoff Routing:** Same sample as #3
   - Add supervisor for intent classification
   - Route to RAG or Booking agents

5. **Production Deployment:** [AzureFunctions samples](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/AzureFunctions)
   - Deploy to Azure Functions
   - Add HITL for approvals
   - Handle long-running MCP tools

---

## 🔧 Key Differences: Python vs .NET

| Feature | Python | .NET |
|---------|--------|------|
| **Agent Creation** | `ChatAgent(...)` | `ChatClientAgent(...)` or `.CreateAIAgent(...)` |
| **Sequential** | `SequentialBuilder().participants([...]).build()` | `AgentWorkflowBuilder.BuildSequential(...)` |
| **Handoff** | `HandoffBuilder(...).build()` | `AgentWorkflowBuilder.CreateHandoffBuilderWith(...).WithHandoffs(...)` |
| **Tools** | Python functions with `Annotated` | Methods with `[Description]` attribute + `AIFunctionFactory.Create()` |
| **Async** | `async/await` with `asyncio` | `async/await` with `Task` |
| **Streaming** | `async for event in workflow.run_stream()` | `await foreach (var result in workflow.RunAsync())` |

---

## 📦 NuGet Packages

```xml
<ItemGroup>
  <PackageReference Include="Microsoft.Agents.AI" Version="1.0.0-*" />
  <PackageReference Include="Microsoft.Agents.AI.Workflows" Version="1.0.0-*" />
  <PackageReference Include="Azure.AI.OpenAI" Version="2.0.0" />
  <PackageReference Include="Azure.Identity" Version="1.13.1" />
  <PackageReference Include="Azure.AI.Projects" Version="1.0.0-*" /> <!-- For Foundry -->
</ItemGroup>
```

---

## 🌐 Additional Resources

- **[Microsoft Agent Framework GitHub](https://github.com/microsoft/agent-framework)** - Full source code and samples
- **[Microsoft Learn Docs](https://learn.microsoft.com/agent-framework/overview/agent-framework-overview)** - Official documentation
- **[Design Documents](https://github.com/microsoft/agent-framework/tree/main/docs/design)** - Architecture decisions
- **[Python to .NET Migration Samples](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/GettingStarted)** - Side-by-side comparisons

---

## 💡 Tips for Migration

1. **Start Small:** Begin with a single agent, then add orchestration
2. **Use Existing Samples:** Copy-paste from samples and adapt to your use case
3. **Test Incrementally:** Test each agent independently before connecting in workflow
4. **Azure Integration:** Use `DefaultAzureCredential` for production (no API keys in code)
5. **Observability:** Add OpenTelemetry from [Agent_Step08_Observability](https://github.com/microsoft/agent-framework/tree/main/dotnet/samples/GettingStarted/Agents/Agent_Step08_Observability)

---

## 🤝 Support

- **Issues:** [GitHub Issues](https://github.com/microsoft/agent-framework/issues)
- **Discussions:** [GitHub Discussions](https://github.com/microsoft/agent-framework/discussions)
- **Documentation:** [Microsoft Learn](https://learn.microsoft.com/agent-framework/)

---

## 📝 Summary

This Python repository demonstrates:
- ✅ **Handoff Orchestration** - Supervisor routing
- ✅ **Sequential Orchestration** - Multi-step booking flow
- ✅ **Azure Foundry Integration**
- ✅ **Tool Calling** - Function execution
- ✅ **Mock Data** - Demo purposes

All of these patterns are **fully supported in .NET** with equivalent (often simpler) syntax. The .NET samples above provide production-ready implementations you can adapt to your healthcare booking system.
