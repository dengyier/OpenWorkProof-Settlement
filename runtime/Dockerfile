ARG OWP_EXECUTION_IMAGE=openworkproof/execution-test@sha256:e9f19bbf9c9ea9456658e47a0430982f9040fca23fb32c7df7f48850f9ef37dc
FROM ${OWP_EXECUTION_IMAGE}
USER 0:0
COPY verifier_test.py /fixed-tests/verifier_test.py
RUN chmod 0444 /fixed-tests/verifier_test.py
USER 65532:65532
