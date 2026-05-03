# Project Scoping, Literature Collection, Initial Risk Categories for Agentic AI
*Project Scope:* 

*https://www.atlassian.com/work-management/project-management/project-scope*

The scope of this project is to evaluate the main risks and issues associated with the use of Agentic AI systems, and propose mitigation strategies to ensure safe execution of this system. The work of four teams working over 12 weeks will combine into the final deliverables which will ultimately create a suite of “trust benchmark” scenarios for an Agentic AI system to be placed in and measured. Through comparing these scenarios to pre-proposed metrics, various issues and vulnerabilities will be revealed in these scenarios, and mitigation strategies will be implemented to combat these issues, allowing the AI system to function flawlessly. 

The main steps that will need to be undertaken is to first understand what risks to look out for and what kind of risks they are. Creation of threat models along with risk taxonomy models ensure full understanding of the likely risks involved when using Agentic AI systems and will make it easier to benchmark future test scenarios. Understanding what tasks will be delegated to the Agentic AI system, such as file handling, calendar scheduling, etc will also need to be decided, as well as the metrics that will be used measure the safety of the AI system during these said tasks. Through the completion of the previous tasks, production of the test scenarios will begin soon after. Detailed fine-tuning of these scenarios and metrics will ensue over the following weeks to ensure that the test scenarios can return accurate and reliable results. 

The work of these four teams will need to be completed by May 31st, marking the end of the 12 weeks. Certain work from teams will also need to be completed earlier as some teams depend on the work of others, unable to complete their work until the previous group has been completed, such as the Risk Taxonomy and Evaluation Dimensions from WP1 to groups WP2, WP3, and WP4. 


## OWASP TOP 10 

*https://genai.owasp.org/llm-top-10/*

*https://www.vectra.ai/topics/agentic-ai-security#agentic-ai-security-risks-and-threats* 

**Global initiative that encompasses the top 10 security measures for the use of Gen AI.**

**Major risks and their initial categories:**

1. **Prompt Injection** – Security Risk 

- User prompts alter LLM output in unintended ways. Inputs can be manipulated to force model to register prompt data which can lead to negative outcomes. 

2. **Sensitive Information Disclosure** – Privacy and Data Protection Risk 

- LLM’s can unintentionally gain access to sensitive data resulting in privacy violations. It must be ensured that sensitive information must be prevented from entering the training model. 

3. **Supply Chain** – Security Risk / Operational Risk 

- Various issues among the AI supply chain, from the creation of the AI system to its training, and to its deployment can lead to biased outputs, security breaches, and system failures. 

4. **Data and Model Poisoning** – Security Risk 

- Occurs when the training or fine-tuning of the AI model has been manipulated to introduce vulnerabilities within the system, which allows easy unauthorised access to the LLM.  

5. **Improper Output Handling** – Privacy and Data Protection Risk 

- Refers to insufficient validation and sanitisation of information as it is passed through the model, which leads to various issues such as misinformation, or it can become susceptible to prompt injection attacks. 

6. **Excessive Agency** – Operational Risk 

- Excessive functions of the AI model can lead to actions being performed which is out the required need of the model, which can lead to damaging actions 

7. **System Prompt Leakage** – Privacy and Data Protection Risk 

- Refers to prompts that can steer the model to reveal sensitive information that is not meant to be discovered. 

8. **Vector and Embedding Weaknesses** – Security Risk 

- Weaknesses in vectors and embeddings open doors to malicious attackers who can gain access to sensitive information and inject harmful content into the AI model. 

9. **Misinformation** – Operational Risk 

- LLM’s produce false or misleading information, which can lead to security breaches, and also negatively impact the reputation of the AI system. 

10. **Unbounded Consumption** – Security Risk / Operational Risk 

- Interfering AI models that produce outputs based on inputs or queries created by users can disrupt services, which can lead to misinformation, denial of service, as well as model degradation. 


## MITRE ATLAS 

*https://atlas.mitre.org/mitigations/AML.M0003*  

**ATLAS has formed its own frameworks which contain a database of tools and methods which help to mitigate attacks and improve AI security**

Mitigations: (some but not all) 

- Limit Public Release of Information 
- Limit Model Artifact Release
- Passive AI Output Obfuscation 
- Model Hardening 
- Restrict Number of AI Model Queries 
- Control Access to AI Models and Data at Rest 
- Use Ensemble Methods 
- Sanitise Training Data 
- Validate AI model 
- Use Multi-Modal Sensors 
- Input Restoration 
- Restrict Library Loading 
- Encrypt Sensitive Information 
- Code Signing 
- Verify AI Artifacts 
- Vulnerability Scanning 
- User Training 
- Generative AI Guidelines 
- Privileged AI Agent Permissions 
- Human-in-the-loop 
- Memory Hardening 
