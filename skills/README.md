<!-- Arquivo gerado por `praxisforge skills catalog` — não editar à mão. -->

# Catálogo de skills

Skills versionadas em `skills/`. Para criar uma nova, parta de `skills/_template/`.

| Skill | Propósito | Versão | Caminho | Fontes |
|---|---|---|---|---|
| diretrizes-codificacao | Diretrizes de comportamento para escrever, revisar ou refatorar código sem os erros típicos de LLMs — explicitar premissas, preferir a solução mais simples, fazer mudanças cirúrgicas e trabalhar contra critérios de sucesso verificáveis. Use em qualquer tarefa de código que não seja trivial. | 1.0.0 | `skills/diretrizes-codificacao/` | karpathy-guidelines |
| guarda-barra-qualidade | Define a barra de qualidade do projeto como contrato escrito e verificável (CONSTRAINTS.md) e impede que o agente a rebaixe para chegar ao verde — supressões novas, testes pulados ou apagados, asserções removidas, stubs, limites editados para baixo. Use quando não há barra escrita, quando pedirem para "definir padrões"/"quality gates", ou quando um agente estiver silenciando verificações para passar. | 1.0.0 | `skills/guarda-barra-qualidade/` | agent-skills-constraints |
