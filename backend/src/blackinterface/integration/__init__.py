"""L5 — Importers and adapters. The ONLY layer allowed to know NodeIds.

RULES:
  * Everything crossing outward must be translated into `domain` types.
  * READ-ONLY (AGENTS.md I1). Never call OneATS write surfaces:
    `*.PosCtl`, `SysCommon.Force/Unforce`, `OADataModel.Restart/OnlineUpdate`,
    `OATagging.Set*`, `OAAlarm.Ack*/Enable/Disable/Delete/Change*Limit`.
    Full list: docs/30-integration/oneats-dataserver.md section 9.
  * Connect with a dedicated read-only account via UserName, never Anonymous.

Subpackages:
  opcua/   OneATS DataServer client-server adapter (asyncua)
  sld/     SLD extract reader — OUT OF MVP SCOPE (ADR-0002), cross-check only
"""
