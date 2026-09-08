//! Isolated probe of the exact visioncortex version from VTracer 0.6.15's lock.
//! Conversion/serialization follows the MIT-licensed VTracer 0.6.12 Rust core.
//! Input is raw RGBA, so no alternate image decoder or color preprocessing occurs.
use std::{env, fs};
use visioncortex::{Color, ColorImage, PathSimplifyMode, PointF64};
use visioncortex::color_clusters::{Runner, RunnerConfig, KeyingAction, HIERARCHICAL_MAX};

fn main() {
    let args: Vec<String> = env::args().collect();
    assert_eq!(args.len(), 7, "input.rgba width height speckle output.svg segmented.rgba");
    let width: usize = args[2].parse().unwrap();
    let height: usize = args[3].parse().unwrap();
    let speckle: usize = args[4].parse().unwrap();
    let mut pixels = fs::read(&args[1]).unwrap();
    assert_eq!(pixels.len(), width * height * 4);
    let mut transparent = 0;
    let threshold = ((width * 2) as f32 * 0.2) as usize;
    for y in [0, height / 4, height / 2, 3 * height / 4, height - 1] {
        for x in 0..width {
            transparent += usize::from(pixels[(y * width + x) * 4 + 3] == 0);
        }
        if transparent >= threshold { break; }
    }
    let key = if transparent >= threshold {
        let palette = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (0,255,255), (255,0,255)];
        let (r,g,b) = palette.into_iter().find(|&(r,g,b)|
            !pixels.chunks_exact(4).any(|p| p[0] == r && p[1] == g && p[2] == b)
        ).expect("Probe needs a deterministic unused key color");
        for p in pixels.chunks_exact_mut(4) {
            if p[3] == 0 { p.copy_from_slice(&[r,g,b,255]); }
        }
        Color::new(r,g,b)
    } else { Color::default() };
    let image = ColorImage { pixels, width, height };
    let clusters = Runner::new(RunnerConfig {
        diagonal: false, hierarchical: HIERARCHICAL_MAX, batch_size: 25600,
        good_min_area: speckle * speckle, good_max_area: width * height,
        is_same_color_a: 3, is_same_color_b: 1, deepen_diff: 16,
        hollow_neighbours: 1, key_color: key, keying_action: KeyingAction::Discard,
    }, image).run();
    let view = clusters.view();
    fs::write(&args[6], view.to_color_image().pixels).unwrap();
    let mut svg = format!("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!-- Generator: visioncortex VTracer 0.6.12 -->\n<svg version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" width=\"{}\" height=\"{}\">\n", width, height);
    for &index in view.clusters_output.iter().rev() {
        let cluster = view.get_cluster(index);
        let paths = cluster.to_compound_path(&view, false, PathSimplifyMode::Spline,
            45.0_f64.to_radians(), 4.0, 10, 45.0_f64.to_radians());
        let (data, offset) = paths.to_svg_string(true, PointF64::default(), None);
        svg.push_str(&format!("<path d=\"{}\" fill=\"{}\" transform=\"translate({},{})\"/>\n",
            data, cluster.residue_color().to_hex_string(), offset.x, offset.y));
        if env::var_os("CHROMAPATH_PROBE_LOG").is_some() {
            eprintln!("{{\"event\":\"output\",\"id\":{},\"area\":{},\"color\":\"{}\",\"holes\":{},\"merged_into\":{}}}",
                index.0, cluster.area(), cluster.residue_color().to_hex_string(), cluster.holes.len(), cluster.merged_into.0);
        }
    }
    svg.push_str("</svg>\n");
    fs::write(&args[5], svg).unwrap();
}
