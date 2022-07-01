"""ThreatConnect Job App"""

# Update Jun 30 with tcex 3.0.3
# Fix includes the batch delete issue, allegedly

# standard library
from tcex.api.tc.v3.tql.tql_operator import TqlOperator
from tcex import TcEx
from tcex.api.tc.v2.batch import Batch
from job_app import JobApp  # Import default Job App Class (Required)
from datetime import datetime, timedelta

# third-party
from tcex.exit import ExitCode

# first-party
#    from tcex.sessions.external_session import ExternalSession

"""
Delete all IP Addresses with these conditions:

    indicator type: address
    owner: {target}} community
    confidence: 0 or Null
    targeting_status = Available

"""

class App(JobApp):
    """Job App"""

    def __init__(self, _tcex: 'TcEx') -> None:
        """Initialize class properties."""
        super().__init__(_tcex)

        #  bypass cert verification step
        self.tcex.session_tc.verify = False

        # properties
        self.session = None

    def run(self) -> None:

        # run main app logic in this method

        # here is the basic logic re: time
        # set the start date by modifying number of weeks you want to go back in time
        # so if the first indicator was added to the source on 1-1-2019
        # and its 1-1-2022, then set number of weeks to be roughly 104
        # yes there is probably a more efficient way to do this

        start = datetime.now()-timedelta(weeks=100)
        d = datetime.now()
        d2 = d - timedelta(days=7)
        count = 0

        while True:
            # create a unique batch for each run
            batch: 'Batch' = self.tcex.v2.batch('Org1', action='Delete')
            indicators = self.tcex.v3.indicators(params={'sorting': 'id ASC'})

            # tql that matched the criteria set in the requirement
            # iterate back in time in increments of 7 days, load to batch, submit, repeat
            indicators.filter.tql = (
                'typeName in ("Address") and '
                f'ownerName in ("{self.inputs.model.tc_owner}") and '
                f'dateAdded >= "{d2.isoformat()}" and dateAdded < "{d.isoformat()}" and '
                'attributeTargeting_Status like "Available" and '
                '(confidence = 0 or confidence is null)'
                )

            # get to a point where there are no indicators left and break the loop
            # self.tcex.log.info(f' Number of indicators in loop: {count}')
            self.log.info(f' ####### Chunk size {indicators.__len__()} ############')
            self.log.info(f' RANGE: dateAdded >= {d2.isoformat()} and dateAdded < {d.isoformat()}')

            # create batch entry
            if d2 > start:
                for indicator in indicators:
                    ip_address = batch.address(f'{indicator.model.summary}')
                    self.log.info(f' target for deletion => {indicator.model.summary}')
                    # load it up
                    batch.save(ip_address)
                self.log.info('#### Submitting to batch ####')
                batch_status: list = batch.submit_all()
                self.log.info(f'batch-status={batch_status}')
                d = d2
                d2 = d - timedelta(days=7)
            else:
                break