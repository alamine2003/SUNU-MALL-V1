import { View, Text, StyleSheet } from "react-native";

export default function HomeScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Bienvenue sur SUNU MALL</Text>
      <Text style={styles.subtitle}>
        La marketplace arrive bientôt — connecte-moi à l&apos;API catalogue.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  title: { fontSize: 22, fontWeight: "bold" },
  subtitle: { marginTop: 8, color: "#555", textAlign: "center" },
});
