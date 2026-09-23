import androidx.compose.material3.MaterialShapes;
import androidx.graphics.shapes.Morph;
import androidx.graphics.shapes.Cubic;
import androidx.graphics.shapes.RoundedPolygon;
import java.nio.file.*;
import java.util.*;

/** Exports matched cubic control points; Java is only needed to regenerate the asset. */
class ExportLoadingShapes {
    static String cubic(Cubic c) {
        return Arrays.toString(new float[]{c.getAnchor0X(), c.getAnchor0Y(),
            c.getControl0X(), c.getControl0Y(), c.getControl1X(), c.getControl1Y(),
            c.getAnchor1X(), c.getAnchor1Y()});
    }
    static String transition(RoundedPolygon a, RoundedPolygon b) {
        Morph morph = new Morph(a, b);
        List<Cubic> start=morph.asCubics(0), end=morph.asCubics(1);
        StringJoiner curves = new StringJoiner(",\n", "[\n", "\n]");
        for (int j=0; j<start.size(); j++)
            curves.add("[" + cubic(start.get(j)) + "," + cubic(end.get(j)) + "]");
        return curves.toString();
    }
    public static void main(String[] args) throws Exception {
        String[] names = {"SoftBurst", "Cookie9Sided", "Pentagon", "Pill", "Sunny", "Cookie4Sided", "Oval"};
        RoundedPolygon[] shapes = new RoundedPolygon[names.length];
        for (int i=0; i<names.length; i++) {
            shapes[i] = (RoundedPolygon)MaterialShapes.Companion.getClass()
                .getMethod("get" + names[i]).invoke(MaterialShapes.Companion);
        }
        StringJoiner all = new StringJoiner(",\n", "[\n", "\n]\n");
        float scale = 1;
        for (int i=0; i<shapes.length; i++) {
            all.add(transition(shapes[i], shapes[(i+1)%shapes.length]));
            float[] b=shapes[i].calculateBounds(), m=shapes[i].calculateMaxBounds(new float[4]);
            scale=Math.min(scale,Math.max((b[2]-b[0])/(m[2]-m[0]),(b[3]-b[1])/(m[3]-m[1])));
        }
        String determinate=transition(MaterialShapes.Companion.getCircle(), shapes[0]);
        Files.writeString(Path.of(args[0]), "{\"scale\":" + scale + ",\"sequence\":" + all
            + ",\"determinate\":" + determinate + "}\n");
        System.out.println("Exported seven matched rounded-polygon transitions");
    }
}
