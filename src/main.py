import os
import argparse
import igl
import numpy as np
import polyscope as ps
from utilities import find_matches_closest_surface, inpaint, smooth
from cli import parse_arguments

def main():
    # Parse arguments
    arguments = parse_arguments()

    # Initialize polyscope
    ps.init()

    # Get the directory of the current file
    current_folder = os.path.dirname(os.path.abspath(__file__))

    # Load the source mesh
    source_mesh_path = os.path.join(current_folder, arguments.source_mesh)

    vertices, faces = igl.read_triangle_mesh(source_mesh_path)
    vertices_1, faces_1, _, _ = igl.remove_unreferenced(vertices, faces)
    if vertices.shape[0] != vertices_1.shape[0]:
        print("[Warning] Source mesh has unreferenced vertices which were removed")
    normals_1 = igl.per_vertex_normals(vertices_1, faces_1)

    # Load the target mesh
    target_mesh_path = os.path.join(current_folder, arguments.target_mesh)
    vertices, faces = igl.read_triangle_mesh(target_mesh_path)
    vertices_2, faces_2, _, _ = igl.remove_unreferenced(vertices, faces)
    if vertices.shape[0] != vertices_2.shape[0]:
        print("[Warning] Target mesh has unreferenced vertices which were removed")
    normals_2 = igl.per_vertex_normals(vertices_2, faces_2)

    # You can setup your own skin weights matrix W \in R^(|V1| x num_bones) here
    # skin_weights = np.load("source_skinweights.npy")

    # For now, generate simple per-vertex data (can be skinning weights but can be any scalar data)
    skin_weights = np.ones((vertices_1.shape[0], 2))  # our simple rig has only 2 bones
    skin_weights[:, 0] = 0.3  # first bone has an influence of 0.3 on all vertices
    skin_weights[:, 1] = 0.7  # second bone has an influence of 0.7 on all vertices

    number_of_bones = skin_weights.shape[1]

    # Register source and target Mesh geometries, plus their Normals
    ps.register_surface_mesh("SourceMesh", vertices_1, faces_1, smooth_shade=True)
    ps.register_surface_mesh("TargetMesh", vertices_2, faces_2, smooth_shade=True)
    ps.get_surface_mesh("SourceMesh").add_vector_quantity("Normals", normals_1, defined_on="vertices", color=(0.2, 0.5, 0.5))
    ps.get_surface_mesh("TargetMesh").add_vector_quantity("Normals", normals_2, defined_on="vertices", color=(0.2, 0.5, 0.5))

    #
    # Section 3.1 Closest Point Matching
    #
    distance_threshold = 0.05 * igl.bounding_box_diagonal(vertices_2)  # threshold distance D
    distance_threshold_squared = distance_threshold * distance_threshold
    angle_threshold_degrees = 30  # threshold angle theta in degrees

    # for every vertex on the target mesh find the closest point on the source mesh and copy weights over
    matched, interpolated_skin_weights = find_matches_closest_surface(
        vertices_1, faces_1, normals_1, vertices_2, faces_2, normals_2, skin_weights, distance_threshold_squared, angle_threshold_degrees
    )

    # visualize vertices for which we found a match
    ps.get_surface_mesh("TargetMesh").add_scalar_quantity("Matched", matched, defined_on="vertices", cmap="blues")


    #
    # Section 3.2 Skinning Weights Inpainting
    #
    inpainted_weights, success = inpaint(vertices_2, faces_2, interpolated_skin_weights, matched)

    if not success:
        print("[Error] Inpainting failed.")
        exit(0)

    # Visualize the weights for each bone
    ps.get_surface_mesh("TargetMesh").add_scalar_quantity(
        "Bone1", inpainted_weights[:, 0], defined_on="vertices", cmap="blues"
    )
    ps.get_surface_mesh("TargetMesh").add_scalar_quantity(
        "Bone2", inpainted_weights[:, 1], defined_on="vertices", cmap="blues"
    )

    # Optional smoothing
    smoothed_inpainted_weights, vertex_ids_to_smooth = smooth(
        vertices_2, faces_2, inpainted_weights, matched, distance_threshold, num_smooth_iter_steps=10, smooth_alpha=0.2
    )
    ps.get_surface_mesh("TargetMesh").add_scalar_quantity(
        "VertexIDsToSmooth", vertex_ids_to_smooth, defined_on="vertices", cmap="blues"
    )

    # Visualize the smoothed weights for each bone
    ps.get_surface_mesh("TargetMesh").add_scalar_quantity(
        "SmoothedBone1", inpainted_weights[:, 0], defined_on="vertices", cmap="blues"
    )
    ps.get_surface_mesh("TargetMesh").add_scalar_quantity(
        "SmoothedBone2", inpainted_weights[:, 1], defined_on="vertices", cmap="blues"
    )

    ps.show()

if __name__ == "__main__":
    main()