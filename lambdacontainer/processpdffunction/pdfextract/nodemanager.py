

import collections
import typing

import rtree, rtree.index
import pdfminer.layout

from . import pdftypes, path_utils, leafgrid
from .pdftypes import ClassificationNode, NodeId, Bbox

class NodeManager():
  def __init__(
    self,
    layers: typing.List[typing.List[ClassificationNode]],
    width: int,
    height: int,
  ) -> None:
    self.layers: typing.DefaultDict[
      int,
      typing.Set[NodeId]
    ] = collections.defaultdict(set)
    self.nodes: typing.Dict[NodeId, ClassificationNode] = {}
    self.leaf_grid = leafgrid.LeafGrid(
      celems=layers[0],
      width=width,
      height=height,
      step_size=10
    )

    self.indexes: typing.Dict[
      int,
      rtree.index.Index
    ] = {}
    for idx, layer in enumerate(layers):
      self.create_layer(layer_id=idx)
      for node in layer:
        self.layers[idx].add(node.node_id)
        self.nodes[node.node_id] = node
      self.index_layer(layer_idx=idx)

  def create_layer(self, layer_id: int):
    if layer_id in self.layers:
      print("=== Warning: Destroying existing layer {0} ===".format(layer_id))
    self.layers[layer_id] = set()

  def add_node(
    self,
    elem: typing.Union[None, pdfminer.layout.LTComponent],
    bbox: Bbox,
    line: typing.Union[None, path_utils.LinePointsType],
    text: typing.Union[None, str],
    left_right: bool,
    child_ids: typing.List[int],
    layer_id: int,
  ):
    if layer_id not in self.layers:
      self.create_layer(layer_id=layer_id)
    node = ClassificationNode(
      elem=elem,
      bbox=bbox,
      line=line,
      text=text,
      child_ids=child_ids,
    )
    node.left_right = left_right
    for child_id in child_ids:
      self.nodes[child_id].parent_ids.add(node.node_id)
    self.layers[layer_id].add(node.node_id)
    self.nodes[node.node_id] = node
    if layer_id in self.indexes:
      self.indexes[layer_id].add(id=node.node_id, coordinates=node.bbox, obj=None)
    return node

  def index_layer(self, layer_idx: int):
    if layer_idx > 0:
      for node_id in self.layers[layer_idx-1]:
        if len(self.nodes[node_id].parent_ids) == 0:
          # Promote node to next layer if no parent
          self.layers[layer_idx].add(node_id)
    if layer_idx in self.indexes:
      print("=== Warning: Destroying existing index {0} ===".format(layer_idx))
    def insertion_generator(nodes: typing.List[ClassificationNode]):
      for node in nodes:
        yield (node.node_id, node.bbox, None)
    layer_nodes = [self.nodes[node_id] for node_id in self.layers[layer_idx]]
    index = rtree.index.Index(insertion_generator(nodes=layer_nodes))
    self.indexes[layer_idx] = index

  def intersection(self, layer_idx: int, bbox: Bbox):
    node_ids = self.indexes[layer_idx].intersection(coordinates=bbox, objects=False)
    return [ self.nodes[node_id] for node_id in node_ids ]
