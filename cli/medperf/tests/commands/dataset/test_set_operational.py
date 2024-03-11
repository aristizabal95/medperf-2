#
#     @pytest.mark.parametrize(
#         "in_path",
#         [
#             ["data", "labels"],
#             ["in_data", "in_labels"],
#             ["/usr/data/path", "usr/labels/path"],
#         ],
#     )
#     @pytest.mark.parametrize(
#         "out_path",
#         [
#             ["out_data", "out_labels"],
#             ["~/.medperf/data/123/data", "~/.medperf/data/123/labels"],
#         ],
#     )
#     def test_generate_uids_assigns_uids_to_obj_properties(
#         self, mocker, in_path, out_path, preparation
#     ):
#         # Arrange
#         mocker.patch(PATCH_DATAPREP.format("get_folders_hash"), side_effect=lambda x: x)
#         preparation.data_path = in_path[0]
#         preparation.labels_path = in_path[1]
#         preparation.out_datapath = out_path[0]
#         preparation.out_labelspath = out_path[1]
#
#         # Act
#         preparation.generate_uids()
#
#         # Assert
#         assert preparation.in_uid == in_path
#         assert preparation.generated_uid == out_path
#
