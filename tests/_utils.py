class DummyDataManager(object):
    """
    this was originally in pyramid_tm.tests
    it was since moved out
    """

    action = None

    def bind(self, tm):
        self.transaction_manager = tm
        tm.get().join(self)

    def abort(self, transaction):
        self.action = "abort"

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        self.action = "commit"

    def tpc_vote(self, transaction):
        pass

    def tpc_finish(self, transaction):
        pass

    def tpc_abort(self, transaction):  # pragma: no cover
        pass

    def sortKey(self):
        return "dummy:%s" % id(self)
