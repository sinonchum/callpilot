.PHONY: test demo panel

test:
	cd laptop && python3 -m pytest

demo:
	cd laptop && python3 -m orchestrator.demo

panel:
	cd panel && npm test && npm run build
