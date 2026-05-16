class SalesOrderOverride:
    """
    Override Sales Order methods for Petrovise customizations.
    """

    def check_credit_limit(self):
        # No-op: credit limit is checked on save via petrovise.api.check_credit_limit_on_save
        pass
