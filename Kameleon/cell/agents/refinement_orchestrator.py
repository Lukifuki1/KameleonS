#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from distillation_engine import run_full_distillation
from elixir_extractor import export_elixir
from kameleon import Kameleon
from loguru import logger
from model_integrity_verifier import verify_all_model_hashes
from orchestrator_shared import knowledge_lock
from vm_fusion_runner import run_vm_models


class RefinementOrchestrator:
    def __init__(self):
        self.kameleon = Kameleon()
        self.integrity_ok = False

    def run(self, models: list[str], max_items: int = 25):
        logger.info("REFINEMENT: začetek postopka izpopolnjevanja znanja")

        self.integrity_ok = self._verify_integrity()
        if not self.integrity_ok:
            logger.warning("REFINEMENT: integriteta modelov ni zagotovljena")
            return

        prompts = export_elixir()
        if not prompts:
            logger.warning("REFINEMENT: ni eliksirja za obdelavo")
            return

        run_full_distillation(models=models, max_items=max_items)

        test_prompt = prompts[0]
        test_exec = run_vm_models(prompt=test_prompt, model_names=models)

        if not test_exec or not any(r.get("output") for r in test_exec):
            logger.warning("REFINEMENT: VM preverjanje ni uspelo")
            return

        with knowledge_lock:
            self.kameleon.sync_with_brain()

        logger.success("REFINEMENT: uspešno zaključeno")

    def _verify_integrity(self) -> bool:
        report = verify_all_model_hashes()
        bad = [i for i in report if i.get("status") not in ("OK", "NEW")]
        return len(bad) == 0
