
from gke_customization.gke_catalog.doc_events.qr_code_maker import get_qr_code

# class Batch(Document):
def validate(self,method):
    self.qr_code = get_qr_code(self.name)