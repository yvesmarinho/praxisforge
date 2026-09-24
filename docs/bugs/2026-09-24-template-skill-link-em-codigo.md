<!-- Criado em: 24/09/2026 16:54 -->
<!-- Modificado em: 24/09/2026 16:54 -->

# Skill criada do template era inválida: link de exemplo em código contava como referência (feature 008)

## Sintoma

Ao rodar o quickstart da feature 008 (T042), uma skill copiada de `skills/_template/` e marcada
como autoral falhava na validação:

```
exemplo-skill: references: 'exemplos/exemplo.md' não encontrado
0 ok, 1 com falha
```

Com isso a publicação recusava a skill, e todo curador que seguisse o template receberia o erro.

## Causa

`extract_references` aplicava a regex de links Markdown sobre o corpo inteiro, incluindo código
inline e blocos cercados. A instrução do template mostra o formato de link entre crases
(`[exemplo](exemplos/exemplo.md)`), e esse exemplo era tratado como referência a um arquivo de
apoio. Os testes unitários não cobriam links dentro de código, e o teste do template só conferia
o frontmatter, não validava uma cópia do template.

## Correção

- Teste de reprodução `test_extract_references_ignora_codigo_inline_e_blocos` (vermelho antes).
- `domain/skill.py`: remove blocos cercados (```````/`~~~`) e código inline antes de extrair links.
- Regressão `test_skill_copiada_do_template_valida`: copia o template, marca como autoral e
  valida pela CLI.

## Verificação

- Quickstart refeito do zero: validar → publicar → inalterada → recusada (mesma versão) →
  atualizada (atalho) → terceiro intacto → órfã listada/removida com `--prune`.
- Lição: todo template precisa de um teste que valide **uma cópia** dele, não só o seu formato.
