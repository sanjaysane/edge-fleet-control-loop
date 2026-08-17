import pathlib
p=pathlib.Path("verifier/persona.yaml")
txt=p.read_text()
txt=txt.replace("  - id: verification_proof", 
"""  - id: scaling
    question: "Is k8s scaling story present (deployment + HPA + log-processor scaling + onboarding workflow)?"
    requires: "k8s/*.yaml + workflows/device_onboarding.py + scale_test/harness.py"
  - id: verification_proof""")
p.write_text(txt)
print("persona updated")
