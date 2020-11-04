from ..base_loss import *
from .tensor_models import *
import torch as th
import torch.nn.functional as functional

logsigmoid = functional.logsigmoid
softplus  = functional.softplus
sigmoid = functional.sigmoid

class HingeLoss(BaseHingeLoss):
    def __init__(self, margin):
        super(HingeLoss, self).__init__(margin)

    def __call__(self, score: th.Tensor, label):
        loss = self.margin - label * score
        loss[loss < 0] = 0
        return loss

class LogisticLoss(BaseLogisticLoss):
    def __init__(self):
        super(LogisticLoss, self).__init__()

    def __call__(self, score: th.Tensor, label):
        return softplus(-label * score)

class BCELoss(BaseBCELoss):
    def __init__(self):
        super(BCELoss, self).__init__()

    def __call__(self, score: th.Tensor, label):
        return -(label * th.log(sigmoid(score)) + (1 - label) * th.log(1 - sigmoid(score)))

class LogsigmoidLoss(BaseLogsigmoidLoss):
    def __init__(self):
        super(LogsigmoidLoss, self).__init__()

    def __call__(self, score: th.Tensor, label):
        return - logsigmoid(label * score)


class LossGenerator(BaseLossGenerator):
    def __init__(self, args, loss_genre='Logistic', neg_label=-1, neg_adversarial_sampling=False, adversarial_temperature=1.0,
                 pairwise=False):
        super(LossGenerator, self).__init__(loss_genre, neg_label, neg_adversarial_sampling, adversarial_temperature, pairwise, has_edge_importance)
        if self.loss_genre == 'Hinge':
            self.neg_label = -1
            self.loss_criterion = HingeLoss(args.margin)
        elif self.loss_genre == 'Logistic':
            self.neg_label = -1
            self.loss_criterion = LogisticLoss()
        elif self.loss_genre == 'Logsigmoid':
            self.neg_label = -1
            self.loss_criterion = LogsigmoidLoss()
        elif self.loss_genre == 'BCE':
            self.neg_label = 0
            self.loss_criterion = BCELoss()
        else:
            raise ValueError('loss genre %s is not support' % self.loss_genre)

    def _get_pos_loss(self, pos_score, edge_weight):
        return self.loss_criterion(pos_score, 1) * edge_weight

    def _get_neg_loss(self, neg_score, edge_weight):
        return self.loss_criterion(neg_score, self.neg_label) * edge_weight

    def get_total_loss(self, pos_score, neg_score, edge_weight=None):
        log = {}
        if edge_weight is None:
            edge_weight = 1
        if self.pairwise:
            pos_score = pos_score.unsqueeze(-1)
            loss = th.mean(self.loss_criterion((pos_score - neg_score) * edge_weight, 1))
            log['loss'] = get_scalar(loss)
            return loss, log
        pos_loss = self._get_pos_loss(pos_score, edge_weight)
        neg_loss = self._get_neg_loss(neg_score, edge_weight)
        # MARK - would average twice make loss function lose precision?
        # do mean over neg_sample
        if self.neg_adversarial_sampling:
            neg_loss = th.sum(th.softmax(neg_score * self.adversarial_temperature, dim=-1).detach() * neg_loss, dim=-1)
        else:
            neg_loss = th.mean(neg_loss, dim=-1)
        # do mean over chunk
        neg_loss = th.mean(neg_loss)
        pos_loss = th.mean(pos_loss)
        loss = (neg_loss + pos_loss) / 2
        log['pos_loss'] = get_scalar(pos_loss)
        log['neg_loss'] = get_scalar(neg_loss)
        log['loss'] = get_scalar(loss)
        return loss, log







